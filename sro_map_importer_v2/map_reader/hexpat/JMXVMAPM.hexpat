struct MapVertex
{
    float Height;
    u16 TextureData;
    u8 Brightness;
};

struct MapBlock
{
    u32 Flag;
    u16 EnvironmentID;
    MapVertex VertexMap[17*17];
    u8 WaterType;
    u8 WaterWaveType;
    float WaterHeight;   
    u16 TileMap[16*16];
     
    float HeightMax;
    float HeightMin;
    u8 reserved[20]; 
};

struct JMXVMAPM
{
    char Signature[12];
    MapBlock Blocks[6*6];     
};

JMXVMAPM file @ 0;