def flatmap(func, iterable):
    return [item for sublist in map(func, iterable) for item in sublist]