from datetime import datetime, timezone
from typing import List, Optional

from sqlmodel import and_, col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.configs.logger import log
from src.domain.constants.jira import JiraIssueStatus, JiraIssueType
from src.domain.models.database.jira_issue import JiraIssueDBCreateDTO, JiraIssueDBUpdateDTO
from src.domain.models.jira_issue import JiraIssueModel
from src.domain.models.jira_sprint import JiraSprintModel
from src.domain.models.jira_user import JiraUserModel
from src.domain.repositories.jira_issue_repository import IJiraIssueRepository
from src.infrastructure.entities.jira_issue import JiraIssueEntity
from src.infrastructure.entities.jira_issue_sprint import JiraIssueSprintEntity
from src.infrastructure.entities.jira_sprint import JiraSprintEntity
from src.infrastructure.entities.jira_user import JiraUserEntity


class SQLAlchemyJiraIssueRepository(IJiraIssueRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_jira_issue_id(self, jira_issue_id: str, include_deleted: bool = False) -> Optional[JiraIssueModel]:
        query = select(JiraIssueEntity).where(col(JiraIssueEntity.jira_issue_id) == jira_issue_id)

        # Filter out deleted issues unless explicitly requested
        if not include_deleted:
            query = query.where(col(JiraIssueEntity.is_deleted) == False)  # noqa: E712

        result = await self.session.exec(query)
        entity = result.first()
        return self._to_domain(entity) if entity else None

    async def create(self, issue: JiraIssueDBCreateDTO) -> JiraIssueModel:
        try:
            issue_model = JiraIssueDBCreateDTO._to_domain(issue)
            # Create issue entity
            issue_entity = self._to_entity(issue_model)
            self.session.add(issue_entity)
            await self.session.flush()  # Flush to get the issue ID

            # Create sprint relationships
            if issue_model.sprints:
                for sprint in issue_model.sprints:
                    # Get or create sprint
                    await self._get_or_create_sprint(sprint)

                    # Create issue-sprint relationship
                    issue_sprint = JiraIssueSprintEntity(
                        jira_issue_id=issue_model.jira_issue_id,
                        jira_sprint_id=sprint.jira_sprint_id,
                        created_at=datetime.now(timezone.utc)
                    )
                    self.session.add(issue_sprint)

            await self.session.commit()
            await self.session.refresh(issue_entity)
            return self._to_domain(issue_entity)

        except Exception as e:
            await self.session.rollback()
            log.error(f"Error creating issue: {str(e)}")
            raise

    async def update(self, issue_id: str, issue_update: JiraIssueDBUpdateDTO) -> JiraIssueModel:
        try:
            # Fetch existing issue
            result = await self.session.exec(
                select(JiraIssueEntity).where(
                    col(JiraIssueEntity.jira_issue_id) == issue_id
                )
            )
            issue_entity = result.first()

            if not issue_entity:
                raise ValueError(f"Issue with jira_issue_id {issue_id} not found")

            # Convert existing entity to domain model
            existing_issue = self._to_domain(issue_entity)

            # Combine existing data with update data
            updated_issue = self._merge_update_with_existing(existing_issue, issue_update)

            # Convert back to entity and update fields
            updated_entity = self._to_entity(updated_issue)
            for key, value in updated_entity.model_dump(exclude={'id', 'sprints'}).items():
                if value is not None:  # Only update non-None values
                    setattr(issue_entity, key, value)

            # Handle sprint updates if present
            if issue_update.sprints is not None:
                # Remove existing relationships
                issue_sprints_result = await self.session.exec(
                    select(JiraIssueSprintEntity).where(
                        col(JiraIssueSprintEntity.jira_issue_id) == issue_id
                    )
                )
                issue_sprints = issue_sprints_result.all()

                # Delete existing relationships
                for issue_sprint in issue_sprints:
                    await self.session.delete(issue_sprint)

                # Create new relationships
                for sprint in issue_update.sprints:
                    await self._get_or_create_sprint(sprint)
                    issue_sprint = JiraIssueSprintEntity(
                        jira_issue_id=issue_id,
                        jira_sprint_id=sprint.jira_sprint_id,
                        created_at=datetime.now(timezone.utc)
                    )
                    self.session.add(issue_sprint)

            await self.session.commit()
            await self.session.refresh(issue_entity)
            return self._to_domain(issue_entity)

        except Exception as e:
            await self.session.rollback()
            log.error(f"Error updating issue: {str(e)}")
            raise

    def _merge_update_with_existing(
        self,
        existing: JiraIssueModel,
        update: JiraIssueDBUpdateDTO
    ) -> JiraIssueModel:
        """Merge update DTO with existing model to create a complete domain model"""
        # Convert update to dict and filter out None values
        update_dict = update.model_dump(exclude_unset=True)

        # Create a new dict with existing data
        merged_data = existing.model_dump()

        # Update only the fields that are present in the update
        for key, value in update_dict.items():
            if value is not None:
                merged_data[key] = value

        # Special handling for enums
        if 'status' in update_dict:
            merged_data['status'] = JiraIssueStatus(update_dict['status'])
        if 'type' in update_dict:
            merged_data['type'] = JiraIssueType(update_dict['type'])

        # Create new domain model with merged data
        return JiraIssueModel(**merged_data)

    async def _get_or_create_sprint(self, sprint: JiraSprintModel) -> JiraSprintEntity:
        # Try to get existing sprint
        result = await self.session.exec(
            select(JiraSprintEntity).where(
                col(JiraSprintEntity.jira_sprint_id) == sprint.jira_sprint_id
            )
        )
        sprint_entity = result.first()

        if not sprint_entity:
            # Create new sprint if it doesn't exist
            sprint_entity = JiraSprintEntity(
                jira_sprint_id=sprint.jira_sprint_id,
                name=sprint.name,
                state=sprint.state,
                start_date=sprint.start_date,
                end_date=sprint.end_date,
                complete_date=sprint.complete_date,
                goal=sprint.goal,
                project_key=sprint.project_key,
                created_at=sprint.created_at,
                updated_at=sprint.updated_at
            )
            self.session.add(sprint_entity)
            await self.session.flush()

        return sprint_entity

    async def get_all(self, include_deleted: bool = False) -> List[JiraIssueModel]:
        """Get all issues, optionally including deleted ones"""
        query = select(JiraIssueEntity)

        # Filter out deleted issues unless explicitly requested
        if not include_deleted:
            query = query.where(col(JiraIssueEntity.is_deleted) == False)  # noqa: E712

        result = await self.session.exec(query)
        entities = result.all()
        return [self._to_domain(entity) for entity in entities]

    def _to_entity(self, model: JiraIssueModel) -> JiraIssueEntity:
        return JiraIssueEntity(
            jira_issue_id=model.jira_issue_id,
            key=model.key,
            summary=model.summary,
            description=model.description,
            status=model.status.value,
            type=model.type.value,
            priority_id=model.priority.id if model.priority else None,
            estimate_point=model.estimate_point,
            actual_point=model.actual_point,
            project_key=model.project_key,
            reporter_id=model.reporter_id,
            assignee_id=model.assignee_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            last_synced_at=model.last_synced_at,
            updated_locally=model.updated_locally,
            is_system_linked=model.is_system_linked,
            is_deleted=model.is_deleted,
            link_url=model.link_url
        )

    def _to_domain(self, entity: JiraIssueEntity) -> JiraIssueModel:
        # Map sprints
        sprints = [
            JiraSprintModel(
                jira_sprint_id=sprint.jira_sprint_id,
                name=sprint.name,
                state=sprint.state,
                start_date=sprint.start_date,
                end_date=sprint.end_date,
                complete_date=sprint.complete_date,
                goal=sprint.goal,
                created_at=sprint.created_at,
                updated_at=sprint.updated_at,
                id=sprint.id
            ) for sprint in entity.sprints
        ]

        # Map assignee if exists
        assignee = None
        if entity.assignee:
            assignee = JiraUserModel(
                id=entity.assignee.id,
                jira_account_id=entity.assignee.jira_account_id,
                email=entity.assignee.email,
                avatar_url=entity.assignee.avatar_url,
                is_system_user=entity.assignee.is_system_user,
                name=entity.assignee.name,
                user_id=entity.assignee.user_id
            )

        return JiraIssueModel(
            key=entity.key,
            summary=entity.summary,
            description=entity.description,
            status=JiraIssueStatus(entity.status),
            type=JiraIssueType(entity.type),
            estimate_point=entity.estimate_point,
            actual_point=entity.actual_point,
            project_key=entity.project_key,
            reporter_id=entity.reporter_id,
            assignee_id=entity.assignee_id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            last_synced_at=entity.last_synced_at,
            jira_issue_id=entity.jira_issue_id,
            updated_locally=entity.updated_locally,
            sprints=sprints,
            id=entity.id,
            is_system_linked=entity.is_system_linked,
            assignee=assignee,
            is_deleted=entity.is_deleted,
            link_url=entity.link_url
        )

    async def get_project_issues(
        self,
        project_key: str,
        sprint_id: Optional[int] = None,
        is_backlog: Optional[bool] = None,
        issue_type: Optional[JiraIssueType] = None,
        search: Optional[str] = None,
        include_deleted: bool = False,
        limit: int = 50
    ) -> List[JiraIssueModel]:
        """Get project issues with filters"""
        try:
            # Base query with user join
            query = (
                select(JiraIssueEntity)
                .outerjoin(JiraUserEntity, col(JiraIssueEntity.assignee_id) == col(JiraUserEntity.jira_account_id))
                .where(col(JiraIssueEntity.project_key) == project_key)
            )

            # Filter out deleted issues unless explicitly requested
            if not include_deleted:
                query = query.where(col(JiraIssueEntity.is_deleted) == False)  # noqa: E712

            # Add sprint filter
            if sprint_id or is_backlog is not None:
                log.info(f"Sprint ID: {sprint_id}, Is backlog: {is_backlog}")
                if sprint_id:
                    # Join with issue_sprint table to filter by sprint_id
                    query = query.join(
                        JiraIssueSprintEntity,
                        col(JiraIssueEntity.jira_issue_id) == col(JiraIssueSprintEntity.jira_issue_id)
                    ).join(
                        JiraSprintEntity,
                        col(JiraIssueSprintEntity.jira_sprint_id) == col(JiraSprintEntity.jira_sprint_id)
                    ).where(col(JiraSprintEntity.id) == sprint_id)
                elif is_backlog:
                    # Issues with has no sprints or all sprints are closed but task is not done yet, are backlog
                    subquery = select(JiraIssueEntity.jira_issue_id).join(
                        JiraIssueSprintEntity,
                        col(JiraIssueEntity.jira_issue_id) == col(JiraIssueSprintEntity.jira_issue_id)
                    ).join(
                        JiraSprintEntity,
                        col(JiraIssueSprintEntity.jira_sprint_id) == col(JiraSprintEntity.jira_sprint_id)
                    ).where(
                        and_(
                            col(JiraSprintEntity.state).not_in(['active', 'future']),
                            col(JiraIssueEntity.status) != JiraIssueStatus.DONE.value
                        )
                    )

                    query = query.where(
                        col(JiraIssueEntity.jira_issue_id).in_(subquery)
                    )

            else:
                log.info("No sprint ID or is_backlog provided")
                query = query.join(
                    JiraIssueSprintEntity,
                    col(JiraIssueEntity.jira_issue_id) == col(JiraIssueSprintEntity.jira_issue_id)
                )
            # Add issue type filter
            if issue_type:
                query = query.where(col(JiraIssueEntity.type) == issue_type.value)

            # Add search filter
            if search:
                search_pattern = f"%{search}%"
                query = query.where(
                    (col(JiraIssueEntity.summary).ilike(search_pattern)) |
                    (col(JiraIssueEntity.description).ilike(search_pattern))
                )

            # Add limit
            query = query.limit(limit)

            # Order by created_at desc to get newest issues first
            query = query.order_by(col(JiraIssueEntity.created_at).desc())

            # Execute query
            result = await self.session.exec(query)
            entities = result.all()

            # Convert to domain models with user info
            return [self._to_domain(entity) for entity in entities]

        except Exception as e:
            log.error(f"Error fetching project issues: {str(e)}")
            raise

    async def get_by_jira_issue_key(self, jira_issue_key: str) -> Optional[JiraIssueModel]:
        """Get issue by key from database"""
        query = select(JiraIssueEntity).where(col(JiraIssueEntity.key) == jira_issue_key)
        result = await self.session.exec(query)
        entity = result.first()
        return self._to_domain(entity) if entity else None

    async def get_issues_by_keys(self, keys: List[str]) -> List[JiraIssueModel]:
        """Get multiple issues by their Jira keys"""
        try:
            log.debug(f"[REPO] Fetching {len(keys)} issues by keys: {keys}")

            query = select(JiraIssueEntity).where(
                and_(
                    col(JiraIssueEntity.key).in_(keys),
                    col(JiraIssueEntity.is_deleted).is_(False)
                )
            )

            log.debug(f"[REPO] Executing query: {query}")
            result = await self.session.exec(query)
            entities = result.all()
            log.debug(f"[REPO] Found {len(entities)} issues in database")

            # Convert to domain models
            return [self._to_domain(entity) for entity in entities]

        except Exception as e:
            log.error(f"[REPO] Error getting issues by keys: {str(e)}", exc_info=True)
            raise

    async def reset_system_linked_for_sprint(self, sprint_id: int) -> int:
        """Reset is_system_linked flag to False for all issues in a sprint"""
        try:
            log.info(f"[REPO] Resetting is_system_linked flag for issues in sprint {sprint_id}")

            # Get the sprint entity first
            sprint_result = await self.session.exec(
                select(JiraSprintEntity).where(col(JiraSprintEntity.id) == sprint_id)
            )
            sprint_entity = sprint_result.first()

            if not sprint_entity:
                log.warning(f"[REPO] Sprint with ID {sprint_id} not found")
                return 0

            # Find all issues in this sprint
            query = (
                select(JiraIssueEntity)
                .join(
                    JiraIssueSprintEntity,
                    col(JiraIssueEntity.jira_issue_id) == col(JiraIssueSprintEntity.jira_issue_id)
                )
                .where(
                    and_(
                        col(JiraIssueSprintEntity.jira_sprint_id) == sprint_entity.jira_sprint_id,
                        col(JiraIssueEntity.is_system_linked).is_(True),
                        col(JiraIssueEntity.is_deleted).is_(False)
                    )
                )
            )

            result = await self.session.exec(query)
            issues = result.all()

            if not issues:
                log.info(f"[REPO] No system-linked issues found in sprint {sprint_id}")
                return 0

            # Update all issues in this sprint to reset is_system_linked flag
            count = 0
            for issue in issues:
                issue.is_system_linked = False
                issue.updated_at = datetime.now(timezone.utc)
                count += 1

            await self.session.commit()
            log.info(f"[REPO] Reset is_system_linked flag for {count} issues in sprint {sprint_id}")
            return count

        except Exception as e:
            await self.session.rollback()
            log.error(f"[REPO] Error resetting is_system_linked for sprint {sprint_id}: {str(e)}", exc_info=True)
            raise
