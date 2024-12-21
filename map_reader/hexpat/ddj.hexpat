struct Texture {
    char buff[12];
    u32 texture_size;
    u32 texture_type;
    u8 texture_buffer[texture_size - 8];
};

Texture file @ 0;

typedef enum texture_type { 
  D3DRTYPE_SURFACE        = 1,
  D3DRTYPE_VOLUME         = 2,
  D3DRTYPE_TEXTURE        = 3,
  D3DRTYPE_VOLUMETEXTURE  = 4,
  D3DRTYPE_CUBETEXTURE    = 5,
  D3DRTYPE_VERTEXBUFFER   = 6,
  D3DRTYPE_INDEXBUFFER    = 7,
  D3DRTYPE_FORCE_DWORD    = 0x7fffffff
};