struct BMS {
    char signature[12];

    u32 offset;
    u32 skin_offset;
    u32 face_offset;
    u32 cloth_vertex_offset;
    u32 cloth_edge_offset;
    u32 bbox_offset;
    u32 occlusion_portals;
    u32 nav_mesh_offset;
    u32 skinned_nav_mesh_offset;
    u32 unknown_offset;
    u32 unknown_flag;
    u32 nav_flag;
    
    u32 sub_prim_count;
    u32 vertex_flag;
    u32 unknown_int_2;
    
    u32 name_len;
    char name[name_len];
    
    u32 material_len;
    char material_name[material_len];
    
    u32 unknown_int_3;
    
    
};

BMS bms  @0;