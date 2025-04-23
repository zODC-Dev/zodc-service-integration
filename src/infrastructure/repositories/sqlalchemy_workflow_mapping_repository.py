from datetime import datetime, timezone
from typing import List, Optional

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.configs.logger import log
from src.domain.models.workflow_mapping import WorkflowMappingModel
from src.domain.repositories.workflow_mapping_repository import IWorkflowMappingRepository
from src.infrastructure.entities.workflow_mapping import WorkflowMappingEntity


class SQLAlchemyWorkflowMappingRepository(IWorkflowMappingRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, workflow_mapping: WorkflowMappingModel) -> WorkflowMappingModel:
        try:
            entity = WorkflowMappingEntity(
                workflow_id=workflow_mapping.workflow_id,
                transaction_id=workflow_mapping.transaction_id,
                project_key=workflow_mapping.project_key,
                sprint_id=workflow_mapping.sprint_id,
                name=workflow_mapping.name,
                description=workflow_mapping.description,
                status=workflow_mapping.status,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )

            self.session.add(entity)
            await self.session.commit()
            await self.session.refresh(entity)

            return self._to_domain(entity)
        except Exception as e:
            await self.session.rollback()
            log.error(f"Error creating workflow mapping: {str(e)}")
            raise

    async def get_by_workflow_id(self, workflow_id: str) -> Optional[WorkflowMappingModel]:
        try:
            query = select(WorkflowMappingEntity).where(col(WorkflowMappingEntity.workflow_id) == workflow_id)
            result = await self.session.exec(query)
            entity = result.first()

            return self._to_domain(entity) if entity else None
        except Exception as e:
            log.error(f"Error fetching workflow mapping by ID: {str(e)}")
            raise

    async def get_by_transaction_id(self, transaction_id: str) -> Optional[WorkflowMappingModel]:
        try:
            query = select(WorkflowMappingEntity).where(col(WorkflowMappingEntity.transaction_id) == transaction_id)
            result = await self.session.exec(query)
            entity = result.first()

            return self._to_domain(entity) if entity else None
        except Exception as e:
            log.error(f"Error fetching workflow mapping by transaction ID: {str(e)}")
            raise

    async def get_by_sprint(self, sprint_id: int) -> List[WorkflowMappingModel]:
        try:
            query = select(WorkflowMappingEntity).where(
                (col(WorkflowMappingEntity.sprint_id) == sprint_id) &
                (col(WorkflowMappingEntity.status) == "active")
            )
            result = await self.session.exec(query)
            entities = result.all()

            return [self._to_domain(entity) for entity in entities]
        except Exception as e:
            log.error(f"Error fetching workflow mappings by sprint: {str(e)}")
            raise

    async def get_by_project(self, project_key: str) -> List[WorkflowMappingModel]:
        try:
            query = select(WorkflowMappingEntity).where(
                (col(WorkflowMappingEntity.project_key) == project_key) &
                (col(WorkflowMappingEntity.status) == "active")
            )
            result = await self.session.exec(query)
            entities = result.all()

            return [self._to_domain(entity) for entity in entities]
        except Exception as e:
            log.error(f"Error fetching workflow mappings by project: {str(e)}")
            raise

    async def update_status(self, workflow_id: str, status: str) -> Optional[WorkflowMappingModel]:
        try:
            stmt = select(WorkflowMappingEntity).where(
                col(WorkflowMappingEntity.workflow_id) == workflow_id
            )

            result = await self.session.exec(stmt)
            entity = result.first()

            if entity:
                entity.status = status
                entity.updated_at = datetime.now(timezone.utc)

            # .values(
            #     status=status,
            #     updated_at=datetime.now(timezone.utc)
            # )
            self.session.add(entity)
            await self.session.commit()

            # Fetch updated entity
            await self.session.refresh(entity)

            return self._to_domain(entity) if entity else None
        except Exception as e:
            await self.session.rollback()
            log.error(f"Error updating workflow mapping status: {str(e)}")
            raise

    def _to_domain(self, entity: WorkflowMappingEntity) -> WorkflowMappingModel:
        return WorkflowMappingModel(
            id=entity.id,
            workflow_id=entity.workflow_id,
            transaction_id=entity.transaction_id,
            project_key=entity.project_key,
            sprint_id=entity.sprint_id,
            name=entity.name,
            description=entity.description,
            status=entity.status,
            created_at=entity.created_at,
            updated_at=entity.updated_at
        )
