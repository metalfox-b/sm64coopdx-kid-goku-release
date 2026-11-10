if not _G.charSelectExists then return end

local RUN_BOOST = 1.15
local JUMP_BOOST = 1.1
local KICK_PUSH = 26
local KICK_HITS = 24
local READY_FRAMES = 60
local JUMPS = {
    [ACT_JUMP] = true, [ACT_DOUBLE_JUMP] = true, [ACT_TRIPLE_JUMP] = true, [ACT_BACKFLIP] = true, [ACT_SIDE_FLIP] = true,
    [ACT_WALL_KICK_AIR] = true,
}

function goku_before_phys_step(m)
    if m.action == ACT_WALKING then
        m.vel.x = m.vel.x * RUN_BOOST
        m.vel.z = m.vel.z * RUN_BOOST
    end
end

function goku_on_set_action(m)
    if JUMPS[m.action] and m.vel.y > 0 then
        m.vel.y = m.vel.y * JUMP_BOOST
    elseif m.action == ACT_JUMP_KICK then

        m.forwardVel = math.max(m.forwardVel, KICK_PUSH)
        m.flags = m.flags | MARIO_ACTION_SOUND_PLAYED
    elseif m.action == ACT_DIVE or m.action == ACT_SLIDE_KICK or m.action == ACT_FLYING_TRIPLE_JUMP then
        m.flags = m.flags | MARIO_MARIO_SOUND_PLAYED
    elseif m.action == ACT_MOVE_PUNCHING and m.actionArg == 0 then
        m.actionArg = 1
    end
end

local LINKS = 13
local LENGTH = 8.6 * 9 / LINKS
local LINK_MODEL = 10
local THICK = {0.9, 0.92, 0.95, 0.98, 1, 1, 1.02, 1.04, 1}
local DEG = 0x10000 / 360

local REST = {-18, -12, -3, 18, 44, 66, 80, 70, 40}
local STREAM = {-34, -22, -10, 0, 8, 18, 30, 42, 50}
local ARC = {-30, -4, 24, 46, 56, 46, 20, -8, -34}
local FLAT = {-50, -40, -24, -10, -4, 0, 4, 12, 24}
local LIES_DOWN = {goku_nimbus_lie = true, goku_sleep_back_50 = true}
local SPRING = {0.55, 0.46, 0.38, 0.32, 0.27, 0.23, 0.2, 0.18, 0.16}
local KEEP = {0.45, 0.52, 0.58, 0.63, 0.67, 0.7, 0.73, 0.75, 0.77}
local DRAG = {0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.1, 0.11}
local JOLT = {0.1, 0.14, 0.18, 0.22, 0.26, 0.3, 0.33, 0.36, 0.38}
local FAR = 200
local DRAG_TOP = 14
local JOLT_TOP = 12
local FEET = {MARIO_ANIM_PART_LEFT_FOOT, MARIO_ANIM_PART_RIGHT_FOOT}
local RAISED = 0.5
local OUT = 8
local CLEAR = 110 * DEG
local DODGE_EASE = 0.35

local CLEARS_KICK = {goku_side_kick_in = true, goku_side_kick_out = true, goku_side_kick2_in = true, goku_side_kick2_out = true}

local function along(table)
    local out = {}
    for j = 1, LINKS do
        local at = 1 + (j - 1) * (#table - 1) / (LINKS - 1)
        local low = math.floor(at)
        local high = math.min(low + 1, #table)
        out[j] = table[low] + (table[high] - table[low]) * (at - low)
    end
    return out
end
THICK, REST, STREAM, ARC, FLAT = along(THICK), along(REST), along(STREAM), along(ARC), along(FLAT)
SPRING, KEEP, DRAG, JOLT = along(SPRING), along(KEEP), along(DRAG), along(JOLT)

local function goku_is(m)
    return obj_has_model_extended(m.marioObj, E_MODEL_GOKU) ~= 0
end

local function wrap(a)
    return (a + 0x8000) % 0x10000 - 0x8000
end

local function clamp(v, low, high)
    return math.max(low, math.min(high, v))
end

function goku_body_yaw(m)
    local gfx = m.marioObj.header.gfx
    local name = smlua_anim_util_get_current_animation_name(m.marioObj)
    local turns = name and GOKU_CLIP_YAW[name]
    if not turns then return gfx.angle.y end
    return gfx.angle.y + turns[math.max(0, math.min(gfx.animInfo.animFrame, #turns - 1)) + 1]
end

local function rest_tail(g, back)
    g.tailX, g.tailY, g.tailZ, g.tailOldX, g.tailOldY, g.tailOldZ = {[0] = 0}, {[0] = 0}, {[0] = 0}, {}, {}, {}
    for j = 1, LINKS do
        local up = math.floor(REST[j] * DEG)
        local level = coss(up) * LENGTH
        g.tailX[j] = g.tailX[j - 1] + sins(back) * level
        g.tailY[j] = g.tailY[j - 1] + sins(up) * LENGTH
        g.tailZ[j] = g.tailZ[j - 1] + coss(back) * level
        g.tailOldX[j], g.tailOldY[j], g.tailOldZ[j] = g.tailX[j], g.tailY[j], g.tailZ[j]
    end
end

local function swing_tail(g, m, back, x, y, z, size)
    local mx, my, mz = 0, 0, 0
    if g.tailRootX then mx, my, mz = x - g.tailRootX, y - g.tailRootY, z - g.tailRootZ end
    if mx * mx + my * my + mz * mz > FAR * FAR then mx, my, mz = 0, 0, 0 end
    local ax, ay, az = mx - (g.tailMoveX or mx), my - (g.tailMoveY or my), mz - (g.tailMoveZ or mz)
    g.tailRootX, g.tailRootY, g.tailRootZ, g.tailMoveX, g.tailMoveY, g.tailMoveZ = x, y, z, mx, my, mz
    ax, ay, az = clamp(ax, -JOLT_TOP, JOLT_TOP), clamp(ay, -JOLT_TOP, JOLT_TOP), clamp(az, -JOLT_TOP, JOLT_TOP)
    local moved = math.sqrt(mx * mx + my * my + mz * mz)
    local trail = moved > DRAG_TOP and DRAG_TOP / moved or 1

    g.tailTime = g.tailTime + 1
    local t = g.tailTime
    local riding = m.action == ACT_GOKU_NIMBUS
    local air = m.action & ACT_FLAG_AIR ~= 0 and not riding
    local speed = math.min(math.sqrt(mx * mx + mz * mz) / 30, 1)
    local stream = speed * (air and 0.6 or 1)
    local shape = riding and ARC or STREAM
    local lying = LIES_DOWN[smlua_anim_util_get_current_animation_name(m.marioObj) or ""]
    g.tailLying = (g.tailLying or 0) + ((lying and 1 or 0) - (g.tailLying or 0)) * 0.08
    local tense = 0
    if m.action == ACT_GOKU_KAME then
        if m.actionState == 0 then tense = 1 else stream, tense = 1, 0.5 end
    elseif m.action == ACT_IDLE and (g.ready or 0) > 0 then
        tense = 0.5
    end

    g.tailPhase = (g.tailPhase or 0) + 0x240 + 0x500 * stream + 0x700 * tense
    local phase = g.tailPhase

    local ground = (riding and m.pos.y - 24 * g.tailLying or m.floorHeight) + 4 - y

    local dodge = 0
    local hip = y - m.floorHeight
    for _, part in ipairs(CLEARS_KICK[smlua_anim_util_get_current_animation_name(m.marioObj) or ""] and FEET or {}) do
        local foot = m.marioBodyState.animPartsPos[part + 1]
        local fx, fz = foot.x - x, foot.z - z
        if hip > 1 and (foot.y - m.floorHeight) / hip > RAISED and fx * fx + fz * fz > (OUT * size) ^ 2 then
            local diff = wrap(atan2s(fz, fx) - back)
            if math.abs(diff) < CLEAR then
                local was = g.tailDodge or 0
                local side = math.abs(was) > 10 * DEG and (was > 0 and 1 or -1) or (diff >= 0 and -1 or 1)
                dodge = diff + side * CLEAR
            end
        end
    end
    g.tailDodge = (g.tailDodge or 0) + (dodge - (g.tailDodge or 0)) * DODGE_EASE

    local px, py, pz = 0, 0, 0
    local reach = LENGTH * size
    for j = 1, LINKS do
        local out = 1 + (j - 1) * 8 / (LINKS - 1)
        local curl = sins(math.floor(phase - out * 0x1500)) * (2 + 3 * out) * (1 + 0.5 * stream)
        local rise = REST[j] + (shape[j] - REST[j]) * stream + 10 * tense + curl
        rise = rise + (FLAT[j] - rise) * g.tailLying
        local sway = coss(math.floor(phase * 0.67 - out * 0x1100)) * (1 - 0.5 * stream) * (1 - 0.6 * g.tailLying) * (2 + 3.6 * out)

        local yaw = back + math.floor((sway + (6 + 2.6 * out) * (1 - stream) + 24 * g.tailLying) * DEG + g.tailDodge)
        local up = math.floor(rise * DEG)
        local level = coss(up) * reach
        local wx, wy, wz = px + sins(yaw) * level, py + sins(up) * reach, pz + coss(yaw) * level

        local nx, ny, nz = g.tailX[j], g.tailY[j], g.tailZ[j]
        local keep = KEEP[j]
        local drag, jolt = DRAG[j] * trail, JOLT[j]
        local vx = (nx - g.tailOldX[j]) * keep - mx * drag - ax * jolt
        local vy = (ny - g.tailOldY[j]) * keep - my * drag - ay * jolt
        local vz = (nz - g.tailOldZ[j]) * keep - mz * drag - az * jolt
        g.tailOldX[j], g.tailOldY[j], g.tailOldZ[j] = nx, ny, nz
        nx, ny, nz = nx + vx, ny + vy, nz + vz
        local spring = SPRING[j]
        nx, ny, nz = nx + (wx - nx) * spring, ny + (wy - ny) * spring, nz + (wz - nz) * spring
        if ny < ground then ny = ground end

        local dx, dy, dz = nx - px, ny - py, nz - pz
        local long = math.sqrt(dx * dx + dy * dy + dz * dz)
        if long < 0.01 then dx, dy, dz, long = wx - px, wy - py, wz - pz, reach end
        local fit = reach / long
        nx, ny, nz = px + dx * fit, py + dy * fit, pz + dz * fit
        g.tailX[j], g.tailY[j], g.tailZ[j] = nx, ny, nz
        px, py, pz = nx, ny, nz
    end
end

local function place_tail(root)
    local i = network_local_index_from_global(root.oGokuOwner)
    local m = gMarioStates[i]
    local g = gGoku[i]
    if not m or not g.tailLinks then return end
    local gfx = m.marioObj.header.gfx
    local torso = m.marioBodyState.torsoPos
    local back = goku_body_yaw(m) + 0x8000
    local hidden = goku_gone(m) or gfx.node.flags & GRAPH_RENDER_ACTIVE == 0
        or gfx.node.flags & GRAPH_RENDER_INVISIBLE ~= 0

    local x, y, z = torso.x + sins(back) * 8, torso.y + 2, torso.z + coss(back) * 8
    local size = gfx.scale.y
    local tick = get_global_timer()
    if not g.tailX then rest_tail(g, back) end
    if g.tailTick ~= tick then
        g.tailTick = tick
        swing_tail(g, m, back, x, y, z, size)
    end

    local reachX, reachZ = g.tailX[LINKS], g.tailZ[LINKS]
    local heading = reachX * reachX + reachZ * reachZ > 1 and atan2s(reachZ, reachX) or back
    local crossX, crossZ = coss(heading), -sins(heading)
    for j = 1, LINKS do
        local o = g.tailLinks[j]
        local dx, dy, dz = g.tailX[j] - g.tailX[j - 1], g.tailY[j] - g.tailY[j - 1], g.tailZ[j] - g.tailZ[j - 1]
        if goku_alive(o) then
            local link = o.header.gfx
            link.pos.x, link.pos.y, link.pos.z = x + g.tailX[j - 1], y + g.tailY[j - 1], z + g.tailZ[j - 1]

            local pitch, yaw = wrap(-atan2s(math.sqrt(dx * dx + dz * dz), dy)), wrap(atan2s(dz, dx))
            local long = math.max(math.sqrt(dx * dx + dy * dy + dz * dz), 0.01)
            local along = (dx * crossX + dz * crossZ) / long
            local wantX, wantY, wantZ = crossX - along * dx / long, -along * dy / long, crossZ - along * dz / long
            local upX, upY, upZ = sins(pitch) * sins(yaw), coss(pitch), sins(pitch) * coss(yaw)
            local roll = atan2s(wantX * coss(yaw) - wantZ * sins(yaw), wantX * upX + wantY * upY + wantZ * upZ)
            link.angle.x, link.angle.y, link.angle.z = pitch, yaw, wrap(roll)
            link.scale.x, link.scale.y, link.scale.z = THICK[j] * size, THICK[j] * size, LENGTH / LINK_MODEL * size

            local flags = link.node.flags & ~GRAPH_RENDER_INVISIBLE
            link.node.flags = hidden and flags | GRAPH_RENDER_INVISIBLE or flags
        end
    end
end

id_bhvGokuTail = hook_behavior(nil, OBJ_LIST_DEFAULT, true, function(o)
    o.oFlags = 0
end, function(o)
    local i = network_local_index_from_global(o.oGokuOwner)
    local m = i and i >= 0 and gMarioStates[i] or nil
    if not m or m.marioObj.header.gfx.sharedChild == nil or not goku_is(m) or not gNetworkPlayers[i].connected then
        if m then gGoku[i].tail, gGoku[i].tailLinks = nil, nil end
        obj_mark_for_deletion(o)
    end
end, "bhvGokuTail")

local BALL_WAITING, BALL_HELD = 0.5, 0.26
local BALL_AHEAD = 11
hook_event(HOOK_UPDATE, function()
    local o = obj_get_first_with_behavior_id(id_bhvWingCap)
    while o do
        local node = o.header.gfx.node
        local ball, faces = obj_has_model_extended(o, E_MODEL_GOKU_DRAGON_BALL) ~= 0, node.flags & GRAPH_RENDER_BILLBOARD ~= 0
        if ball and not faces then
            obj_set_billboard(o)
            o.hookRender = 1
        elseif faces and not ball then
            node.flags = node.flags & ~GRAPH_RENDER_BILLBOARD
            o.hookRender = 0
            obj_scale(o, 1)
        end
        o = obj_get_next_with_same_behavior_id(o)
    end
end)

local function place_carried(o)
    local i = network_local_index_from_global(o.oGokuOwner)
    local m = i and i >= 0 and gMarioStates[i] or nil
    if not m then return end
    local hand, elbow = m.marioBodyState.animPartsPos[MARIO_ANIM_PART_LEFT_HAND + 1], m.marioBodyState.animPartsPos[MARIO_ANIM_PART_LEFT_FOREARM + 1]
    local dx, dy, dz = hand.x - elbow.x, hand.y - elbow.y, hand.z - elbow.z
    local reach = BALL_AHEAD / math.max(math.sqrt(dx * dx + dy * dy + dz * dz), 1)
    local gfx, his = o.header.gfx, m.marioObj.header.gfx
    gfx.pos.x, gfx.pos.y, gfx.pos.z = hand.x + dx * reach, hand.y + dy * reach, hand.z + dz * reach
    gfx.scale.x, gfx.scale.y, gfx.scale.z = BALL_HELD, BALL_HELD, BALL_HELD
    local hidden = goku_gone(m) or his.node.flags & GRAPH_RENDER_ACTIVE == 0 or his.node.flags & GRAPH_RENDER_INVISIBLE ~= 0
    local flags = gfx.node.flags & ~GRAPH_RENDER_INVISIBLE
    gfx.node.flags = hidden and flags | GRAPH_RENDER_INVISIBLE or flags
end

id_bhvGokuCarried = hook_behavior(nil, OBJ_LIST_DEFAULT, true, function(o)
    o.oFlags = 0
    o.hookRender = 1
    obj_set_billboard(o)
end, function(o)
    local i = network_local_index_from_global(o.oGokuOwner)
    local m = i and i >= 0 and gMarioStates[i] or nil
    if not m or not goku_is(m) or not gNetworkPlayers[i].connected or m.flags & MARIO_WING_CAP == 0 then
        if m then gGoku[i].carried = nil end
        obj_mark_for_deletion(o)
    end
end, "bhvGokuCarried")

local function carry_update(m, g)
    if m.flags & MARIO_WING_CAP == 0 then return end
    local owner = network_global_index_from_local(m.playerIndex)
    local o = g.carried
    if goku_alive(o) and get_id_from_behavior(o.behavior) == id_bhvGokuCarried and o.oGokuOwner == owner then return end
    g.carried = spawn_non_sync_object(id_bhvGokuCarried, E_MODEL_GOKU_DRAGON_BALL, m.pos.x, m.pos.y, m.pos.z, function(ball)
        ball.oGokuOwner = owner
    end)
end

hook_event(HOOK_ON_OBJECT_RENDER, function(o)
    local id = get_id_from_behavior(o.behavior)
    if id == id_bhvGokuTail and o.oAction == 1 then
        place_tail(o)
    elseif id == id_bhvGokuCarried then
        place_carried(o)
    elseif id == id_bhvWingCap and obj_has_model_extended(o, E_MODEL_GOKU_DRAGON_BALL) ~= 0 then

        local gfx = o.header.gfx
        gfx.scale.x, gfx.scale.y, gfx.scale.z = BALL_WAITING, BALL_WAITING, BALL_WAITING
        gfx.pos.y = o.oPosY + 50 * BALL_WAITING
    end
end)

local LEAP, LEAP_BIG, TAP = {"goku_leap.ogg", 0.5}, {"goku_leap_big.ogg", 0.6}, {"goku_land_tap.ogg", 0.5}
local ACTION_SOUNDS = {
    [ACT_JUMP] = LEAP, [ACT_DOUBLE_JUMP] = LEAP_BIG, [ACT_TRIPLE_JUMP] = LEAP_BIG, [ACT_BACKFLIP] = LEAP_BIG,
    [ACT_SIDE_FLIP] = LEAP_BIG, [ACT_LONG_JUMP] = LEAP_BIG, [ACT_WALL_KICK_AIR] = LEAP_BIG,
    [ACT_FLYING_TRIPLE_JUMP] = {"goku_lets_go.ogg", 1},
    [ACT_DIVE] = {"goku_shout_aryaa.ogg", 1}, [ACT_JUMP_KICK] = {"goku_shout_orya.ogg", 1},
    [ACT_JUMP_LAND] = TAP, [ACT_FREEFALL_LAND] = TAP, [ACT_DOUBLE_JUMP_LAND] = TAP, [ACT_TRIPLE_JUMP_LAND] = TAP,
    [ACT_BACKFLIP_LAND] = TAP, [ACT_SIDE_FLIP_LAND] = TAP, [ACT_LONG_JUMP_LAND] = TAP,
}

local SWING, SWING_BIG = {"goku_swing.ogg", 0.7}, {"goku_swing_big.ogg", 0.8}
local PUNCH, HEAVY_PUNCH, HEAVY_KICK = {"goku_punch.ogg", 0.8}, {"goku_heavy_punch.ogg", 0.9}, {"goku_heavy_kick.ogg", 0.9}
local CLIP_SOUNDS = {rock_in = SWING, scissors_in = SWING, paper = SWING_BIG, gp_land = HEAVY_PUNCH, kick = SWING_BIG, lunge = SWING_BIG,
    slide_kick = SWING_BIG, side_kick_in = SWING_BIG, side_kick2_in = SWING_BIG,}

local SHOUTS = {side_kick_in = "goku_shout_ya.ogg", side_kick2_in = "goku_shout_ha2.ogg", slide_kick = "goku_shout_arya.ogg"}

local IMPACTS = {paper = HEAVY_PUNCH, kick = HEAVY_KICK, lunge = HEAVY_KICK, lunge_skid = HEAVY_KICK,
    slide_kick = HEAVY_KICK, side_kick_in = HEAVY_KICK, side_kick_out = HEAVY_KICK, side_kick2_in = HEAVY_KICK, side_kick2_out = HEAVY_KICK,
    stomp_enemy = HEAVY_KICK}
local SAME_BLOW = 8
local STOMP_FRAMES = 24
local STOMP_HOLD = 3
local GRIN_FRAMES = 24

local FIGHTING = {[ACT_PUNCHING] = true, [ACT_MOVE_PUNCHING] = true, [ACT_JUMP_KICK] = true, [ACT_DIVE] = true,
    [ACT_DIVE_SLIDE] = true, [ACT_SLIDE_KICK] = true, [ACT_SLIDE_KICK_SLIDE] = true, [ACT_GROUND_POUND_LAND] = true,
    [ACT_GOKU_KAME] = true, [ACT_BACKFLIP_LAND] = true, [ACT_BACKFLIP_LAND_STOP] = true}

local function fight_update(m, g)
    if FIGHTING[m.action] then
        g.ready = READY_FRAMES
    elseif (g.ready or 0) > 0 then
        g.ready = g.ready - 1
    end
    if m.action == ACT_MOVE_PUNCHING then
        g.punchLanded = g.punchLanded or g.lastAction == ACT_PUNCHING
    else
        g.punchLanded = false
    end
    g.lastAction = m.action
    if m.action == ACT_JUMP_KICK and m.marioObj.header.gfx.animInfo.animFrame < KICK_HITS then
        m.flags = m.flags | MARIO_KICKING
    end

    m.marioBodyState.punchState = 0

    local o = m.marioObj
    if m.action == ACT_MOVE_PUNCHING then
        o.oActiveParticleFlags = o.oActiveParticleFlags | ACTIVE_PARTICLE_DUST
        g.dustHeld = true
    elseif g.dustHeld then
        o.oActiveParticleFlags = o.oActiveParticleFlags & ~ACTIVE_PARTICLE_DUST
        g.dustHeld = false
    end

    if m.action == ACT_DIVE then m.marioObj.header.gfx.angle.x = 0 end

    if m.action == ACT_MOVE_PUNCHING and not g.punchLanded then
        if m.actionArg == 3 then m.actionArg = 4 end
        if m.actionArg == 6 then m.flags = m.flags | MARIO_ACTION_SOUND_PLAYED end
    end
end

hook_event(HOOK_ON_ATTACK_OBJECT, function(m, o, interaction)
    if m.playerIndex ~= 0 or not goku_is(m) or interaction & INT_HIT_FROM_ABOVE == 0 then return end
    gGoku[0].stomped, gGoku[0].landed = true, true
    gGoku[0].stompY = o.oPosY + o.hitboxHeight
end)

hook_event(HOOK_ON_PLAY_SOUND, function(sound, pos)
    if sound == SOUND_ACTION_BOUNCE_OFF_OBJECT and gGoku[0].stomped then return NO_SOUND end
    if sound ~= SOUND_ACTION_HIT_2 then return end
    for i = 0, MAX_PLAYERS - 1 do
        local m = gMarioStates[i]
        local from = m.marioObj.header.gfx.cameraToObject
        if gNetworkPlayers[i].connected and goku_is(m) and from.x == pos.x and from.y == pos.y and from.z == pos.z then
            gGoku[i].landed = true
            return NO_SOUND
        end
    end
end)

local song
local CAP_FADE = 60
function goku_load_song()
    if mod_file_exists("sound/goku_wing_song.ogg") then song = audio_stream_load("goku_wing_song.ogg") end
    if song then audio_stream_set_looping(song, true) end
end
local function song_wanted(m)
    return song ~= nil and goku_is(m) and m.flags & MARIO_WING_CAP ~= 0
end
hook_event(HOOK_ON_SEQ_LOAD, function(player, seqId)
    if player == SEQ_PLAYER_LEVEL and seqId & 0x7F == gLevelValues.wingCapSequence & 0x7F and song_wanted(gMarioStates[0]) then
        gGoku[0].songSwapped = true
        return SEQ_SOUND_PLAYER
    end
end)
function goku_song_update(m)
    local g, on = gGoku[0], song_wanted(m)
    if on and not g.songOn then audio_stream_play(song, true, 1) end
    if not on and g.songOn then audio_stream_stop(song) end
    if on then audio_stream_set_volume(song, math.min(1, m.capTimer / CAP_FADE)) end
    g.songOn = on
end

local function stomp_update(m, g)
    local sync = gPlayerSyncTable[m.playerIndex]
    local count = sync.gokuStomps or 0
    local stomped = g.stomped or (m.playerIndex ~= 0 and g.stompsSeen ~= nil and count ~= g.stompsSeen)
    g.stomped = false
    if stomped and m.playerIndex == 0 then
        count = count + 1
        sync.gokuStomps = count
    end
    g.stompsSeen = count
    if stomped and m.action & ACT_FLAG_AIR ~= 0 and m.action ~= ACT_TWIRLING then
        g.stompLeft, g.stompAction = STOMP_FRAMES, m.action
        if m.playerIndex == 0 then g.stompHold, g.stompX, g.stompZ, g.stompVy = STOMP_HOLD, m.pos.x, m.pos.z, m.vel.y end
    end
    if (g.stompLeft or 0) <= 0 then return end
    if m.action ~= g.stompAction then
        g.stompLeft, g.stompHold = 0, 0
        return
    end

    set_character_animation(m, CHAR_ANIM_A_POSE)
    goku_anim(m, "goku_stomp_enemy")
    set_anim_to_frame(m, STOMP_FRAMES - g.stompLeft)
    g.stompLeft = g.stompLeft - 1
    if (g.stompHold or 0) > 0 then
        g.stompHold = g.stompHold - 1
        m.pos.x, m.pos.y, m.pos.z, m.vel.y = g.stompX, g.stompY, g.stompZ, g.stompVy
    end
end

local function impact_sounds(m, g)
    local sync = gPlayerSyncTable[m.playerIndex]
    local count = sync.gokuHits or 0
    local landed = g.landed or (m.playerIndex ~= 0 and g.hitsHeard ~= nil and count ~= g.hitsHeard)
    g.landed = false
    if landed and m.playerIndex == 0 then
        count = count + 1
        sync.gokuHits = count
    end
    g.hitsHeard = count
    if landed and get_global_timer() - (g.heardAt or -SAME_BLOW) >= SAME_BLOW then
        g.heardAt = get_global_timer()
        g.grinFor = GRIN_FRAMES
        local sound = IMPACTS[g.soundClip and g.soundClip:gsub("^goku_", ""):gsub("_%d+$", "") or ""] or PUNCH
        goku_sound(m, sound[1], sound[2])
    end
end

local function move_sounds(m, g)
    if m.action ~= g.soundAction then
        g.soundAction = m.action
        local sound = ACTION_SOUNDS[m.action]
        if sound then goku_sound(m, sound[1], sound[2]) end
    end
    local name = smlua_anim_util_get_current_animation_name(m.marioObj)
    if name ~= g.soundClip then
        g.soundClip = name
        local clip = name and name:gsub("^goku_", ""):gsub("_%d+$", "")
        local sound = clip and CLIP_SOUNDS[clip]
        if sound then goku_sound(m, sound[1], sound[2]) end
        if clip and SHOUTS[clip] then goku_sound(m, SHOUTS[clip]) end
    end
end

local function level_head(m, g)
    local body = m.marioBodyState
    local walking = m.action == ACT_WALKING and goku_is(m)
    if walking then
        body.allowPartRotation = 1
        body.headAngle.x, body.headAngle.y, body.headAngle.z = -body.torsoAngle.x, 0, 0
    elseif g.headLevel then
        body.allowPartRotation = 0
    end
    g.headLevel = walking
end

hook_event(HOOK_MARIO_UPDATE, function(m)
    local g = gGoku[m.playerIndex]
    level_head(m, g)
    if m.playerIndex == 0 then goku_song_update(m) end

    if not goku_is(m) or not gNetworkPlayers[m.playerIndex].connected then return end
    local hand = m.marioBodyState.handState
    if hand == MARIO_HAND_HOLDING_CAP or hand == MARIO_HAND_HOLDING_WING_CAP then
        m.marioBodyState.handState = MARIO_HAND_OPEN
    end
    fight_update(m, g)
    stomp_update(m, g)
    move_sounds(m, g)
    impact_sounds(m, g)
    goku_wing_update(m)
    carry_update(m, g)
    local owner = network_global_index_from_local(m.playerIndex)

    if goku_alive(g.tail) and get_id_from_behavior(g.tail.behavior) == id_bhvGokuTail and g.tail.oGokuOwner == owner then
        return
    end
    g.tailLinks, g.tailTime, g.tailX, g.tailRootX, g.tailMoveX, g.tailMoveY, g.tailMoveZ = {}, 0, nil, nil, nil, nil, nil
    for j = 1, LINKS do
        g.tailLinks[j] = spawn_non_sync_object(id_bhvGokuTail, E_MODEL_GOKU_TAIL, m.pos.x, m.pos.y, m.pos.z, function(o)
            o.oGokuOwner = owner
            o.oAction = j == 1 and 1 or 0
            o.hookRender = j == 1 and 1 or 0
        end)
    end
    g.tail = g.tailLinks[1]
end)
