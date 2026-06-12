using System.IO.Compression;

namespace EdgeCloudOffloadingTcc.Charts;

public sealed class PngCanvas
{
    private readonly int _width;
    private readonly int _height;
    private readonly byte[] _rgb;

    public PngCanvas(int width, int height, byte r = 255, byte g = 255, byte b = 255)
    {
        _width = width;
        _height = height;
        _rgb = new byte[width * height * 3];
        Clear(r, g, b);
    }

    public void Clear(byte r, byte g, byte b)
    {
        for (var i = 0; i < _rgb.Length; i += 3)
        {
            _rgb[i] = r;
            _rgb[i + 1] = g;
            _rgb[i + 2] = b;
        }
    }

    public void Rect(int x, int y, int w, int h, byte r, byte g, byte b)
    {
        for (var yy = Math.Max(0, y); yy < Math.Min(_height, y + h); yy++)
        for (var xx = Math.Max(0, x); xx < Math.Min(_width, x + w); xx++)
            Pixel(xx, yy, r, g, b);
    }

    public void Line(int x0, int y0, int x1, int y1, byte r, byte g, byte b)
    {
        var dx = Math.Abs(x1 - x0);
        var sx = x0 < x1 ? 1 : -1;
        var dy = -Math.Abs(y1 - y0);
        var sy = y0 < y1 ? 1 : -1;
        var err = dx + dy;
        while (true)
        {
            Pixel(x0, y0, r, g, b);
            if (x0 == x1 && y0 == y1) break;
            var e2 = 2 * err;
            if (e2 >= dy) { err += dy; x0 += sx; }
            if (e2 <= dx) { err += dx; y0 += sy; }
        }
    }

    public void Save(string path)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        using var file = File.Create(path);
        file.Write([137, 80, 78, 71, 13, 10, 26, 10]);
        Chunk(file, "IHDR", Ihdr());
        Chunk(file, "IDAT", Compress(Scanlines()));
        Chunk(file, "IEND", []);
    }

    private void Pixel(int x, int y, byte r, byte g, byte b)
    {
        if (x < 0 || x >= _width || y < 0 || y >= _height) return;
        var i = (y * _width + x) * 3;
        _rgb[i] = r;
        _rgb[i + 1] = g;
        _rgb[i + 2] = b;
    }

    private byte[] Ihdr()
    {
        using var ms = new MemoryStream();
        WriteInt(ms, _width);
        WriteInt(ms, _height);
        ms.WriteByte(8);
        ms.WriteByte(2);
        ms.WriteByte(0);
        ms.WriteByte(0);
        ms.WriteByte(0);
        return ms.ToArray();
    }

    private byte[] Scanlines()
    {
        var row = _width * 3;
        var data = new byte[(_width * 3 + 1) * _height];
        for (var y = 0; y < _height; y++)
        {
            var dst = y * (row + 1);
            data[dst] = 0;
            Buffer.BlockCopy(_rgb, y * row, data, dst + 1, row);
        }
        return data;
    }

    private static byte[] Compress(byte[] data)
    {
        using var ms = new MemoryStream();
        ms.WriteByte(0x78);
        ms.WriteByte(0x9C);
        using (var ds = new DeflateStream(ms, CompressionLevel.SmallestSize, true))
            ds.Write(data, 0, data.Length);
        var adler = Adler32(data);
        WriteInt(ms, unchecked((int)adler));
        return ms.ToArray();
    }

    private static void Chunk(Stream stream, string type, byte[] data)
    {
        WriteInt(stream, data.Length);
        var typeBytes = System.Text.Encoding.ASCII.GetBytes(type);
        stream.Write(typeBytes);
        stream.Write(data);
        var crc = Crc32(typeBytes.Concat(data).ToArray());
        WriteInt(stream, unchecked((int)crc));
    }

    private static void WriteInt(Stream stream, int value)
    {
        stream.WriteByte((byte)((value >> 24) & 255));
        stream.WriteByte((byte)((value >> 16) & 255));
        stream.WriteByte((byte)((value >> 8) & 255));
        stream.WriteByte((byte)(value & 255));
    }

    private static uint Adler32(byte[] data)
    {
        const uint mod = 65521;
        uint a = 1, b = 0;
        foreach (var value in data)
        {
            a = (a + value) % mod;
            b = (b + a) % mod;
        }
        return (b << 16) | a;
    }

    private static uint Crc32(byte[] data)
    {
        uint crc = 0xffffffff;
        foreach (var b in data)
        {
            crc ^= b;
            for (var i = 0; i < 8; i++)
                crc = (crc & 1) == 1 ? 0xedb88320 ^ (crc >> 1) : crc >> 1;
        }
        return ~crc;
    }
}
