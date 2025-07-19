# tilemap.py
import pytmx, pygame

class TileMap:
    def __init__(self, filename):
        tm = pytmx.load_pygame(filename, pixelalpha=True)
        self.width, self.height = tm.width, tm.height
        self.tmxdata = tm

    def draw(self, surface):
        for layer in self.tmxdata.visible_layers:
            if hasattr(layer, 'data'):
                for x, y, gid in layer:
                    tile = self.tmxdata.get_tile_image_by_gid(gid)
                    if tile:
                        surface.blit(tile, (x * TILE_SIZE, y * TILE_SIZE))
