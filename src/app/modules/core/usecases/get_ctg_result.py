from app.modules.core.domain.ctg import CTGResult
from app.modules.core.usecases.exceptions import NotFoundObject
from app.modules.core.usecases.ports.ctg import CTGPort


async def get_ctg_result(ctg_id: int, ctg_repo: CTGPort) -> CTGResult:

    ctg_result = await ctg_repo.get_ctg_result(ctg_id)
    if not ctg_result:
        raise NotFoundObject
    return ctg_result