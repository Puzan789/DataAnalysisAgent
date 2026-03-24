from dataclasses import dataclass


@dataclass
class ServiceContainer:
    """Containter holding all the application services."""

    db_state: any
    graph: any


async def create_service_container(db_state) -> ServiceContainer:
    """Factory to create the service container."""

    from src.graph.builder import build_agent_graph

    graph = await build_agent_graph(checkpointer=db_state.checkpointer)

    return ServiceContainer(
        graph=graph,
        db_state=db_state,
    )
