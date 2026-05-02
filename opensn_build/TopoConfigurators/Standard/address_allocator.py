# address_allocator.py

# address_allocator.py

SAT_LINK_BASE = [10, 0, 0, 0]   # satellite inter-links (ISL) — never advertised to Area 0
UT_BASE      = [10, 1, 0, 0]   # GS↔SAT links — in Area 0 directly, not summarized
ANCHOR_BASE       = [10, 3, 0, 0]   # UT↔SAT links — summarized as 10.3.0.0/16 into Area 0
GSL_BASE   = [10, 2, 0, 0]   # GS↔Anchor links

def array_add(base: list, delta: int) -> list:
    ret = [base[i] for i in range(len(base))]
    for i in range(len(base)-1, -1, -1):
        if delta == 0:
            break
        delta = delta + ret[i]
        ret[i] = delta % 256
        delta = delta // 256
    return ret

def alloc_ipv4(prefix_len: int, pool: str = "sat") -> list:
    global SAT_LINK_BASE, GSL_BASE, UT_BASE, ANCHOR_BASE

    if pool == "sat":
        base = SAT_LINK_BASE
    elif pool == "gsl":
        base = GSL_BASE
    elif pool == "ut":
        base = UT_BASE
    elif pool == "anchor":
        base = ANCHOR_BASE
    else:
        raise ValueError(f"Unknown pool: {pool}")

    delta = 1 << (32 - prefix_len)
    subnet = []
    for i in range(delta):
        subnet.append(array_add(base, i))

    new_base = array_add(base, delta)

    if pool == "sat":
        SAT_LINK_BASE = new_base
    elif pool == "gsl":
        GSL_BASE = new_base
    elif pool == "ut":
        UT_BASE = new_base
    elif pool == "anchor":
        ANCHOR_BASE = new_base

    return subnet

def format_ipv4(ip:list, prefix_len: int) -> str:
    if len(ip) < 4:
        raise "invalid ip"
    return "%d.%d.%d.%d/%d"%(ip[0],ip[1],ip[2],ip[3],prefix_len)
    