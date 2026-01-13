class SeriesAccessor:
    def __init__(self, values: list):
        self.values = values

    def value_at(self, offset: int):
        if offset < 0:
            return None
        if offset >= len(self.values):
            return None
        return self.values[offset]
