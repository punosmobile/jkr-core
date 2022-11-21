from typing import TYPE_CHECKING

from jkrimporter.model import Osoite

if TYPE_CHECKING:
    from addrparser import Address


def osoite_from_parsed_address(address: "Address") -> Osoite:

    huoneistotunnus = (
        " ".join(
            part for part in (address.entrance, address.apartment) if part is not None
        )
        or None
    )

    return Osoite(
        katunimi=address.street_name or address.post_office_box,
        osoitenumero=address.house_number,
        huoneistotunnus=huoneistotunnus,
    )
