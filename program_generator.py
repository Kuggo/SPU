import mcschematic

# constants
direction = 0
player_offset = (0, -2, 0)
wide = 2
high = 2
schem = mcschematic.MCSchematic()
game_version = mcschematic.Version.JE_1_18_2

# funcs


def pos(x, y, z=0) -> tuple[int, int, int]:
    if direction == 0:
        return player_offset[0] + x, player_offset[1] + y, player_offset[2] + z
    elif direction == 1:
        return player_offset[0] + z, player_offset[1] + y, player_offset[2] + x
    elif direction == 2:
        return player_offset[0] - x, player_offset[1] + y, player_offset[2] - z
    elif direction == 3:
        return player_offset[0] - z, player_offset[1] + y, player_offset[2] - x


def put(x, y):
    schem.setBlock(pos(x, y), "minecraft:redstone_block")
    return


def put_byte(byte: str, x):
    y = 0
    for bit in byte:
        if bit == '1':
            put(x, y)
        y -= high
    return


# main func


def main():
    with open("output.txt", 'r') as f:
        binary = f.read().split('\n')

    x = 0
    for byte in binary:
        put_byte(byte, x)
        x += wide

    schem.save(outputFolderPath='schems', schemName="bin_schem", version=game_version)

    return


if __name__ == '__main__':
    main()
