
def human_size(size: int) -> str:
    if size < 1024:
        return f'{size}B'
    if size < 1024 ** 2:
        return f'{size / 1024:.1f}K'
    if size < 1024 ** 3:
        return f'{size / 1024 ** 2:.1f}M'
    return f'{size / 1024 ** 3:.1f}G'
