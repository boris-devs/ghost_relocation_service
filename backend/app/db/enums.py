from __future__ import annotations

from enum import Enum


class Lighting(str, Enum):
    DARK = "dark"
    DIM = "dim"
    BRIGHT = "bright"


class Humidity(str, Enum):
    DRY = "dry"
    NORMAL = "normal"
    DAMP = "damp"


class SpecialCondition(str, Enum):
    NEEDS_ATTIC = "needs_attic"                
    FEARS_MIRRORS = "fears_mirrors"             
    NO_HUMANS_NEARBY = "no_humans_nearby"        
    LIKES_DAMPNESS = "likes_dampness"            
    NEEDS_SILENCE = "needs_silence"              
    NEEDS_DARKNESS = "needs_darkness"            
    DISLIKES_CROWDS = "dislikes_crowds"          


SPECIAL_CONDITION_LABELS: dict[SpecialCondition, str] = {
    SpecialCondition.NEEDS_ATTIC: "нужен чердак",
    SpecialCondition.FEARS_MIRRORS: "боится зеркал",
    SpecialCondition.NO_HUMANS_NEARBY: "нельзя селить рядом с людьми",
    SpecialCondition.LIKES_DAMPNESS: "любит сырость",
    SpecialCondition.NEEDS_SILENCE: "нужна тишина",
    SpecialCondition.NEEDS_DARKNESS: "боится яркого света",
    SpecialCondition.DISLIKES_CROWDS: "не любит тесноту",
}
