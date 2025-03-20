from fastapi import APIRouter

router = APIRouter()


# @router.post("", response_model=StandardResponse[JiraCreateIssueResponse])
# async def create_issue(
#     issue: JiraIssueCreateRequest,
#     claims: JWTClaims = Depends(get_jwt_claims),
#     controller: JiraController = Depends(get_jira_controller),
# ) -> StandardResponse[JiraCreateIssueResponse]:
#     """Create a new Jira issue"""
#     user_id = int(claims.sub)
#     return await controller.create_issue(user_id, issue)


# @router.patch("/{issue_id}", response_model=StandardResponse[GetJiraIssueResponse])
# async def update_issue(
#     issue_id: str,
#     update: JiraIssueUpdateRequest,
#     claims: JWTClaims = Depends(get_jwt_claims),
#     controller: JiraController = Depends(get_jira_controller),
# ) -> StandardResponse[GetJiraIssueResponse]:
#     """Update a Jira issue"""
#     user_id = int(claims.sub)
#     return await controller.update_issue(user_id, issue_id, update)
