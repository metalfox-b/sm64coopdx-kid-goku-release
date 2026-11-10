#include "src/game/envfx_snow.h"

const GeoLayout goku_tail_geo[] = {
	GEO_NODE_START(),
	GEO_OPEN_NODE(),
		GEO_DISPLAY_LIST(LAYER_OPAQUE_INTER, goku_tail_goku_tail_mesh_layer_3_with_revert),
		GEO_DISPLAY_LIST(LAYER_OPAQUE, goku_tail_goku_tail_mesh_layer_1_with_revert),
	GEO_CLOSE_NODE(),
	GEO_END(),
};
