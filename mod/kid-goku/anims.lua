if not _G.charSelectExists then return end

GOKU_ANIMS = GOKU_ANIMS or {}
GOKU_CHAR_ANIMS = {}
for slot, name in pairs(GOKU_SLOT_ANIMS) do GOKU_CHAR_ANIMS[slot] = name end

GOKU_CHAR_ANIMS[CHAR_ANIM_A_POSE] = function(m)
    return gGoku[m.playerIndex].anim or GOKU_SLOT_ANIMS[CHAR_ANIM_A_POSE]
end
if CS_ANIM_MENU then GOKU_CHAR_ANIMS[CS_ANIM_MENU] = "goku_menu" end

local FIDGETS = {[1] = "goku_hips", [3] = "goku_flex", [5] = "goku_hips", [7] = "goku_flex"}
local function in_a_fight(m)
    return m.action == ACT_IDLE and (gGoku[m.playerIndex].ready or 0) > 0
end

local FIDGET_SLOT = GOKU_SLOT_ANIMS[CHAR_ANIM_IDLE_HEAD_LEFT]
GOKU_CHAR_ANIMS[CHAR_ANIM_IDLE_HEAD_LEFT] = function(m)
    if in_a_fight(m) then return "goku_fight_ready" end
    return m.action == ACT_IDLE and FIDGETS[m.actionTimer] or FIDGET_SLOT
end
for _, slot in ipairs({CHAR_ANIM_IDLE_HEAD_RIGHT, CHAR_ANIM_IDLE_HEAD_CENTER}) do
    local rest = GOKU_SLOT_ANIMS[slot]
    GOKU_CHAR_ANIMS[slot] = function(m) return in_a_fight(m) and "goku_fight_ready" or rest end
end

local function walk_kick(m)
    local g = gGoku[m.playerIndex]
    return m.action == ACT_MOVE_PUNCHING and g.lastAction ~= ACT_PUNCHING and not g.punchLanded
end
for slot, kick in pairs({[CHAR_ANIM_FIRST_PUNCH] = "goku_side_kick_in", [CHAR_ANIM_FIRST_PUNCH_FAST] = "goku_side_kick_out",
        [CHAR_ANIM_SECOND_PUNCH] = "goku_side_kick2_in", [CHAR_ANIM_SECOND_PUNCH_FAST] = "goku_side_kick2_out"}) do
    local jan_ken = GOKU_SLOT_ANIMS[slot]
    GOKU_CHAR_ANIMS[slot] = function(m) return walk_kick(m) and kick or jan_ken end
end

local LUNGE_SLOT = GOKU_SLOT_ANIMS[CHAR_ANIM_DIVE]
GOKU_CHAR_ANIMS[CHAR_ANIM_DIVE] = function(m)
    return (m.action == ACT_DIVE_SLIDE or m.action == ACT_STOMACH_SLIDE_STOP) and "goku_lunge_skid" or LUNGE_SLOT
end

local WING_SLOT, SPIN_SLOT = GOKU_SLOT_ANIMS[CHAR_ANIM_WING_CAP_FLY], GOKU_SLOT_ANIMS[CHAR_ANIM_FORWARD_SPINNING_FLIP]
GOKU_CHAR_ANIMS[CHAR_ANIM_WING_CAP_FLY] = function(m) return m.action == ACT_FLYING and "goku_nimbus_fly" or WING_SLOT end
GOKU_CHAR_ANIMS[CHAR_ANIM_FORWARD_SPINNING_FLIP] = function(m) return m.action == ACT_FLYING and "goku_nimbus_board" or SPIN_SLOT end
GOKU_CHAR_ANIMS[CHAR_ANIM_TRIPLE_JUMP_FLY] = "goku_nimbus_call"

local TRIPLE_LAND_SLOT = GOKU_SLOT_ANIMS[CHAR_ANIM_TRIPLE_JUMP_LAND]
GOKU_CHAR_ANIMS[CHAR_ANIM_TRIPLE_JUMP_LAND] = function(m)
    return m.action == ACT_BACKFLIP_LAND_STOP and "goku_land_ready" or TRIPLE_LAND_SLOT
end

GOKU_CHAR_HANDS = {
    [CHAR_ANIM_SECOND_PUNCH] = MARIO_HAND_PEACE_SIGN,
    [CHAR_ANIM_SECOND_PUNCH_FAST] = MARIO_HAND_PEACE_SIGN,
    [CHAR_ANIM_GROUND_KICK] = MARIO_HAND_OPEN,
    [CHAR_ANIM_STAR_DANCE] = function(m, frame) return frame > 60 and MARIO_HAND_PEACE_SIGN or MARIO_HAND_FISTS end,
    [CHAR_ANIM_WATER_STAR_DANCE] = function(m, frame) return frame > 60 and MARIO_HAND_PEACE_SIGN or MARIO_HAND_FISTS end,
    [CHAR_ANIM_SWIM_PART1] = MARIO_HAND_OPEN,
    [CHAR_ANIM_SWIM_PART2] = MARIO_HAND_OPEN,
    [CHAR_ANIM_WATER_IDLE] = MARIO_HAND_OPEN,
    [CHAR_ANIM_IDLE_ON_LEDGE] = MARIO_HAND_OPEN,
    [CHAR_ANIM_CREDITS_WAVING] = MARIO_HAND_OPEN,
    [CHAR_ANIM_SLEEP_IDLE] = MARIO_HAND_OPEN,
    [CHAR_ANIM_SLEEP_START_LYING] = MARIO_HAND_OPEN,
    [CHAR_ANIM_SLEEP_LYING] = MARIO_HAND_OPEN,
    [CHAR_ANIM_WALK_PANTING] = MARIO_HAND_OPEN,
    [CHAR_ANIM_A_POSE] = function(m)
        local hands = {goku_kame_charge = MARIO_HAND_OPEN, goku_kame_fire = MARIO_HAND_OPEN,
            goku_nimbus_lie = MARIO_HAND_OPEN}
        return hands[gGoku[m.playerIndex].anim or ""]
    end,
}
