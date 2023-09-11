import pkgutil
import bsdiff4
import os
from random import Random

from BaseClasses import MultiWorld
from worlds.Files import APDeltaPatch
from settings import get_settings

from .items import FE8Item
from .locations import FE8Location
from .constants import FE8_NAME
from .util import write_short_le
from .fe8_rando import FE8Randomizer

BASE_PATCH = "data/base_patch.bsdiff4"
PATCH_FILE_EXT = ".apfe8"

# TODO: populate this into connector_config on basepatch build
SLOT_NAME_OFFS = 0xEFCE78  # archipelagoInfo->slotName
SUPER_DEMON_KING_OFFS = 0xEFCEB8  # archipelagoOptions->superDemonKing

# TODO: move this into `locations.py`
LOCATION_INFO_OFFS = 0xEFCEBC
LOCATION_INFO_SIZE = 4

AP_ITEM_KIND = 1
SELF_ITEM_KIND = 2


class FE8DeltaPatch(APDeltaPatch):
    game = FE8_NAME
    hash = "005531fef9efbb642095fb8f64645236"
    patch_file = PATCH_FILE_EXT
    patch_file_ending = ".gba"

    @classmethod
    def get_source_data(cls) -> bytes:
        return get_base_rom_as_bytes()


def get_base_rom_as_bytes() -> bytes:
    with open(get_settings().fe8_settings.rom_file, "rb") as infile:
        base_rom_bytes = bytes(infile.read())

    return base_rom_bytes


def rom_location(loc: FE8Location):
    return LOCATION_INFO_OFFS + loc.local_address * LOCATION_INFO_SIZE


def generate_output(
    multiworld: MultiWorld, player: int, output_dir: str, random: Random
) -> None:
    base_rom = get_base_rom_as_bytes()
    base_patch = pkgutil.get_data(__name__, BASE_PATCH)
    patched_rom = bytearray(bsdiff4.patch(base_rom, base_patch))

    randomizer = FE8Randomizer(rom=patched_rom, random=random)
    randomizer.apply_changes()

    for location in multiworld.get_locations(player):
        assert isinstance(location, FE8Location)
        rom_loc = rom_location(location)
        if location.item and location.item.player == player:
            assert isinstance(location.item, FE8Item)
            write_short_le(patched_rom, rom_loc, SELF_ITEM_KIND)
            write_short_le(
                patched_rom,
                rom_loc + 2,
                location.item.local_code
            )
        else:
            write_short_le(patched_rom, rom_loc, AP_ITEM_KIND)

    patched_rom[SUPER_DEMON_KING_OFFS] = int(bool(multiworld.super_demon_king[player]))

    for i, byte in enumerate(multiworld.player_name[player].encode("utf-8")):
        patched_rom[SLOT_NAME_OFFS + i] = byte

    outfile_player_name = f"_P{player}"
    outfile_player_name += (
        f"_{multiworld.get_file_safe_player_name(player).replace(' ', '_')}"
        if multiworld.player_name[player] != f"Player{player}"
        else ""
    )

    output_path = os.path.join(
        output_dir, f"AP_{multiworld.seed_name}{outfile_player_name}.gba"
    )
    with open(output_path, "wb") as outfile:
        outfile.write(patched_rom)
    patch = FE8DeltaPatch(
        os.path.splitext(output_path)[0] + PATCH_FILE_EXT,
        player=player,
        player_name=multiworld.player_name[player],
        patched_path=output_path,
    )
    patch.write()
    #os.unlink(output_path)