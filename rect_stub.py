class Rect:
    def __init__(self, pos, size=None):
        if size is None:
            if isinstance(pos, Rect):
                self.x = pos.x
                self.y = pos.y
                self.width = pos.width
                self.height = pos.height
            elif hasattr(pos, "__len__") and len(pos) == 4:
                self.x, self.y, self.width, self.height = pos
            else:
                raise ValueError("Rect expects (x, y, w, h) or Rect")
        else:
            self.x, self.y = pos
            self.width, self.height = size

    @property
    def left(self):
        return self.x

    @property
    def right(self):
        return self.x + self.width

    @property
    def top(self):
        return self.y

    @property
    def bottom(self):
        return self.y + self.height

    @property
    def centerx(self):
        return self.x + self.width / 2

    @property
    def centery(self):
        return self.y + self.height / 2

    @property
    def center(self):
        return (self.centerx, self.centery)

    def collidepoint(self, x, y=None):
        if y is None:
            x, y = x
        return self.left <= x <= self.right and self.top <= y <= self.bottom

    def colliderect(self, other):
        other = Rect(other) if not isinstance(other, Rect) else other
        return not (
            self.right < other.left
            or self.left > other.right
            or self.bottom < other.top
            or self.top > other.bottom
        )

    def inflate(self, dx, dy):
        new_w = self.width + dx
        new_h = self.height + dy
        cx = self.centerx
        cy = self.centery
        return Rect((cx - new_w / 2, cy - new_h / 2), (new_w, new_h))

    def __iter__(self):
        yield int(self.x)
        yield int(self.y)
        yield int(self.width)
        yield int(self.height)

    def __len__(self):
        return 4

    def __getitem__(self, idx):
        return (int(self.x), int(self.y), int(self.width), int(self.height))[idx]

    def __repr__(self):
        return f"Rect({self.x}, {self.y}, {self.width}, {self.height})"
