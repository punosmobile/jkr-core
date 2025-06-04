from sqlalchemy import select, desc
from sqlalchemy.exc import NoResultFound
from datetime import datetime
from jkrimporter.providers.db.models import (
    DVVPoimintaPvm
)

def find_last_dvv_poiminta (session) -> datetime.date:
    vanha_poiminta_query = (
                select(DVVPoimintaPvm)
                .order_by(desc(DVVPoimintaPvm.poimintapvm))
                .limit(1)
            )

    try:
        dvv_poiminta = session.execute(vanha_poiminta_query).scalar_one()
        return dvv_poiminta.poimintapvm
    except NoResultFound:
        return None