import json

from sqlalchemy import create_engine

from jkrimporter import conf
from jkrimporter.providers.db.utils import JSONEncoderWithDateSupport


def json_dumps(value):
    return json.dumps(value, cls=JSONEncoderWithDateSupport)


engine = create_engine(
    "postgresql://{username}:{password}@{host}:{port}/{dbname}".format(**conf.dbconf),
    future=True,
    json_serializer=json_dumps
    # echo=False,
)
