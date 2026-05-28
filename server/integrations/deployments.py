class DeploymentLookupService:
    async def get_recent_deployments(self, service_name: str) -> list[dict[str, object]]:
        if not service_name:
            return []
        return []
