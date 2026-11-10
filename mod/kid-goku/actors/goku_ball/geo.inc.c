#include "src/game/envfx_snow.h"

const GeoLayout goku_ball_geo[] = {
	GEO_NODE_START(),
	GEO_OPEN_NODE(),
		GEO_DISPLAY_LIST(LAYER_TRANSPARENT, goku_ball_goku_ball_mesh_layer_5_with_revert),
	GEO_CLOSE_NODE(),
	GEO_END(),
};
