"""Dependency-free PE export-table dumper.

Usage:
    python pe_exports.py <dll> [substr1 substr2 ...]

With no substrings: prints the count of exports.
With substrings: prints every exported name containing any substring (case-insensitive).

Pure stdlib (struct/mmap) so it runs under the kit's bundled interpreter with no pip.
"""
import sys, struct, mmap


def u16(b, o): return struct.unpack_from("<H", b, o)[0]
def u32(b, o): return struct.unpack_from("<I", b, o)[0]


def rva_to_off(sections, rva):
    for vaddr, vsize, praw in sections:
        if vaddr <= rva < vaddr + vsize:
            return praw + (rva - vaddr)
    return None


def exports(path):
    with open(path, "rb") as f:
        b = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    if b[:2] != b"MZ":
        raise ValueError("not MZ")
    pe = u32(b, 0x3C)
    if b[pe:pe + 4] != b"PE\0\0":
        raise ValueError("not PE")
    coff = pe + 4
    nsec = u16(b, coff + 2)
    opt = coff + 20
    magic = u16(b, opt)
    if magic != 0x20B:
        raise ValueError("not PE32+ (x64)")
    # data directory 0 = export table; sits at opt+112 for PE32+
    exp_rva = u32(b, opt + 112)
    exp_size = u32(b, opt + 116)
    if exp_rva == 0:
        return []
    sizeof_opt = u16(b, coff + 16)
    sectab = opt + sizeof_opt
    sections = []
    for i in range(nsec):
        s = sectab + i * 40
        vsize = u32(b, s + 8)
        vaddr = u32(b, s + 12)
        praw = u32(b, s + 20)
        sections.append((vaddr, max(vsize, u32(b, s + 16)), praw))
    eo = rva_to_off(sections, exp_rva)
    nnames = u32(b, eo + 24)
    names_rva = u32(b, eo + 32)
    no = rva_to_off(sections, names_rva)
    out = []
    for i in range(nnames):
        nrva = u32(b, no + i * 4)
        off = rva_to_off(sections, nrva)
        end = b.find(b"\0", off)
        out.append(b[off:end].decode("ascii", "replace"))
    return out


def main():
    path = sys.argv[1]
    subs = [s.lower() for s in sys.argv[2:]]
    names = exports(path)
    if not subs:
        print(f"{path}: {len(names)} exports")
        return
    hits = [n for n in names if any(s in n.lower() for s in subs)]
    print(f"{path}: {len(names)} exports, {len(hits)} match")
    for n in hits:
        print("  " + n)


if __name__ == "__main__":
    main()
