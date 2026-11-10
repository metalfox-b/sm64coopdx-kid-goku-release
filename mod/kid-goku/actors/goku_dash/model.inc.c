Vtx goku_dash_goku_dash_mesh_layer_5_vtx_0[12] = {
	{{ {0, -20, -16}, 0, {-16, 1008}, {255, 255, 255, 255} }},
	{{ {0, 20, 16}, 0, {1008, 1008}, {255, 255, 255, 255} }},
	{{ {0, 46, 38}, 0, {1008, -16}, {255, 255, 255, 255} }},
	{{ {0, -46, 6}, 0, {-16, -16}, {255, 255, 255, 255} }},
	{{ {0, -46, 6}, 0, {-16, 1008}, {255, 255, 255, 255} }},
	{{ {0, 46, 38}, 0, {1008, 1008}, {255, 255, 255, 255} }},
	{{ {0, 46, 94}, 0, {1008, -16}, {255, 255, 255, 255} }},
	{{ {0, -46, 62}, 0, {-16, -16}, {255, 255, 255, 255} }},
	{{ {0, -46, 62}, 0, {-16, 1008}, {255, 255, 255, 255} }},
	{{ {0, 46, 94}, 0, {1008, 1008}, {255, 255, 255, 255} }},
	{{ {0, 20, 116}, 0, {1008, -16}, {255, 255, 255, 255} }},
	{{ {0, -20, 84}, 0, {-16, -16}, {255, 255, 255, 255} }},
};

Gfx goku_dash_goku_dash_mesh_layer_5_tri_0[] = {
	gsSPVertex(goku_dash_goku_dash_mesh_layer_5_vtx_0 + 0, 12, 0),
	gsSP1Triangle(0, 1, 2, 0),
	gsSP1Triangle(0, 2, 3, 0),
	gsSP1Triangle(4, 5, 6, 0),
	gsSP1Triangle(4, 6, 7, 0),
	gsSP1Triangle(8, 9, 10, 0),
	gsSP1Triangle(8, 10, 11, 0),
	gsSPEndDisplayList(),
};


Gfx mat_goku_dash_goku_dash_Light[] = {
	gsSPClearGeometryMode(G_CULL_BACK | G_LIGHTING),
	gsDPPipeSync(),
	gsDPSetCombineLERP(0, 0, 0, SHADE, 0, 0, 0, SHADE, 0, 0, 0, SHADE, 0, 0, 0, SHADE),
	gsDPSetAlphaDither(G_AD_NOISE),
	gsSPTexture(65535, 65535, 0, 0, 1),
	gsSPEndDisplayList(),
};

Gfx mat_revert_goku_dash_goku_dash_Light[] = {
	gsSPSetGeometryMode(G_CULL_BACK | G_LIGHTING),
	gsDPPipeSync(),
	gsDPSetAlphaDither(G_AD_DISABLE),
	gsSPEndDisplayList(),
};

Gfx goku_dash_goku_dash_mesh_layer_5_with_revert[] = {
	gsSPDisplayList(mat_goku_dash_goku_dash_Light),
	gsSPDisplayList(goku_dash_goku_dash_mesh_layer_5_tri_0),
	gsSPDisplayList(mat_revert_goku_dash_goku_dash_Light),
	gsDPPipeSync(),
	gsSPSetGeometryMode(G_LIGHTING),
	gsSPClearGeometryMode(G_TEXTURE_GEN),
	gsDPSetCombineLERP(0, 0, 0, SHADE, 0, 0, 0, ENVIRONMENT, 0, 0, 0, SHADE, 0, 0, 0, ENVIRONMENT),
	gsSPTexture(65535, 65535, 0, 0, 0),
	gsDPSetEnvColor(255, 255, 255, 255),
	gsDPSetAlphaCompare(G_AC_NONE),
	gsSPEndDisplayList(),
};

