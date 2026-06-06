import unreal
def call(o, n, *a):
    try: return getattr(o, n)(*a)
    except Exception as e: return "ERR(%s)" % str(e)[:50]
real = unreal.load_object(None, "/Game/_Scratch/AM_MF_idle_FB.AM_MF_idle_FB")
print("AM_MF_idle_FB:", real)
print("  play_length:", call(real, "get_play_length"))
print("  num_sections:", call(real, "get_num_sections"))
print("  group_name:", call(real, "get_group_name"))
print("  slot names (lib):", call(unreal.AnimationLibrary, "get_montage_slot_names", real))
# compare: the factory montage (had content, wrong slot)
fac = unreal.load_object(None, "/Game/_Scratch/AM_MF_idle_HORSE.AM_MF_idle_HORSE")
if fac:
    print("AM_MF_idle_HORSE play_length:", call(fac, "get_play_length"), "slots:", call(unreal.AnimationLibrary, "get_montage_slot_names", fac))
