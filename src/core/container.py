from dataclasses import dataclass


@dataclass
class ServiceContainer:
    """Containter holding all the application services."""

    db_state: any
    graph: any
    chart_service: any = None


async def create_service_container(db_state) -> ServiceContainer:
    """Factory to create the service container."""

    from src.graph.builder import build_agent_graph
    from src.services.chart_service import ChartService
    from src.core.utils import get_llm

    graph = await build_agent_graph(checkpointer=db_state.checkpointer)
    chart_service = ChartService(llm=get_llm())

    return ServiceContainer(
        graph=graph,
        db_state=db_state,
        chart_service=chart_service,
    )
