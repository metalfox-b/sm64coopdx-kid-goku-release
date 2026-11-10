if not _G.charSelectExists then return end

ACT_GOKU_KAME = allocate_mario_action(ACT_GROUP_STATIONARY | ACT_FLAG_STATIONARY | ACT_FLAG_ATTACKING)

local KAME_MIN = 14
local KAME_FULL = 90
local BEAM_SPEED = 235
local DASHES = 20
local DASH_GAP = 84
local DASH_FLOW = 46

local CHANT = {{0, "goku_ka.ogg"}, {7, "goku_me.ogg"}, {14, "goku_ha2.ogg"}, {21, "goku_me2.ogg"}}

local RISE_STEP, RISE_STEPS = 15, 6
local CHANT_OVER = 28

local FULL_BLAST_FROM = 45

local CHARGE_DRAW, CHARGE_HOLD = 34, 8
local THRUST, BRACE, RECOVER = 3, 8, 10

local function owner(o)
    local i = network_local_index_from_global(o.oGokuOwner)
    if i == nil or i < 0 or i >= MAX_PLAYERS then return nil end
    local m = gMarioStates[i]
    if goku_gone(m) or m.action ~= ACT_GOKU_KAME then return nil end
    return m
end

local function charge_frame(t)
    if t < CHARGE_DRAW then return t end
    return CHARGE_DRAW + (t - CHARGE_DRAW) % CHARGE_HOLD
end

local function wave_frames(m)
    return math.floor(24 + 26 * m.actionArg / KAME_FULL)
end

local function fire_frame(m, t)
    local stop = wave_frames(m)
    if t < THRUST then return t end
    if t < stop then return THRUST + (t - THRUST) % BRACE end
    return math.min(THRUST + BRACE + t - stop, THRUST + BRACE + RECOVER - 1)
end

local function palms(m, phase, frame)
    local track = GOKU_KAME_PALMS[phase]
    local p = track[math.min(math.max(frame + 1, 1), #track)]
    local s, c = sins(m.faceAngle.y), coss(m.faceAngle.y)
    return m.pos.x + c * p[1] + s * p[3], m.pos.y + p[2], m.pos.z - s * p[1] + c * p[3]
end

local function draw_ball(o, x, y, z, radius)
    o.oPosX, o.oPosY, o.oPosZ = x, y, z
    obj_scale(o, radius / 50)
end

local function init_effect(o)
    o.oFlags = OBJ_FLAG_UPDATE_GFX_POS_AND_ANGLE
    o.oDrawingDistance = 12000
end

local function init_ball(o)
    init_effect(o)
    obj_set_billboard(o)
end

local function spawn_effect(m, behavior, model, init)
    return spawn_non_sync_object(behavior, model, m.pos.x, m.pos.y, m.pos.z, function(o)
        o.oGokuOwner = network_global_index_from_local(m.playerIndex)
        obj_scale(o, 0)
        if init then init(o) end
    end)
end

id_bhvGokuSpark = hook_behavior(nil, OBJ_LIST_DEFAULT, true, init_ball, function(o)
    local m = owner(o)
    local g = m and gGoku[m.playerIndex]
    if not m or m.actionState ~= 0 or o.oTimer >= 12 or not goku_alive(g.ball) then
        obj_mark_for_deletion(o)
        return
    end
    local k = o.oTimer / 12
    local b = g.ball
    local reach = (1 - k * k) * o.oGokuLength
    local yaw, up = o.oGokuTag, o.oGokuCharge
    o.oPosX = b.oPosX + sins(yaw) * coss(up) * reach
    o.oPosY = b.oPosY + sins(up) * reach
    o.oPosZ = b.oPosZ + coss(yaw) * coss(up) * reach
    obj_scale(o, (3 + 3.5 * k) / 50)
end, "bhvGokuSpark")

id_bhvGokuBall = hook_behavior(nil, OBJ_LIST_DEFAULT, true, init_ball, function(o)
    local m = owner(o)
    if not m or gGoku[m.playerIndex].ball ~= o then
        obj_mark_for_deletion(o)
        return
    end
    local firing = m.actionState ~= 0
    local t = math.max(0, m.actionTimer - 1)
    local stop = firing and wave_frames(m)
    if firing and t >= stop then obj_mark_for_deletion(o); return end
    if not firing then
        local g = gGoku[m.playerIndex]
        local beat = math.floor(o.oTimer / RISE_STEP)
        if beat ~= g.riseBeat then
            g.riseBeat = beat
            local swell = math.max(0, m.actionTimer - CHANT_OVER) / (KAME_FULL - CHANT_OVER)
            goku_sound(m, "goku_kame_rise" .. math.min(beat + 1, RISE_STEPS) .. ".ogg", 0.32 + 0.38 * swell)
        end
        if o.oTimer % 2 == 0 then
            spawn_effect(m, id_bhvGokuSpark, E_MODEL_GOKU_BALL, function(s)
                s.oGokuTag = math.random(0, 0xFFFF)
                s.oGokuCharge = math.random(-0x3000, 0x3000)
                s.oGokuLength = 46 + 40 * m.actionTimer / KAME_FULL
            end)
        end
    end
    local x, y, z = palms(m, firing and "fire" or "charge", firing and fire_frame(m, t) or charge_frame(t))
    local q = (firing and m.actionArg or m.actionTimer) / KAME_FULL
    local radius
    if firing then

        local swell = math.min(1, (t + 1) / THRUST) * math.min(1, (stop - t) / 6)
        radius = (18 + 22 * q) * swell * (1 + 0.1 * sins(o.oTimer * 0x3100))
        x, z = x + sins(m.faceAngle.y) * radius * 0.86, z + coss(m.faceAngle.y) * radius * 0.86
    else
        radius = (3 + 15 * q) * (1 + 0.12 * sins(o.oTimer * 0x2700))
    end
    draw_ball(o, x, y, z, radius)
end, "bhvGokuBall")

local head_behavior = hook_behavior(nil, OBJ_LIST_DEFAULT, true, init_ball, function(o)
    local m = owner(o)
    if not m or m.actionState ~= 1 or not goku_alive(o.parentObj) or gGoku[m.playerIndex].beam ~= o.parentObj then
        obj_mark_for_deletion(o)
    end
end, "bhvGokuWaveHead")

local function follow_beam(o)
    if not goku_alive(o.parentObj) or o.parentObj.oGokuOwner ~= o.oGokuOwner then obj_mark_for_deletion(o) end
end
id_bhvGokuDash = hook_behavior(nil, OBJ_LIST_DEFAULT, true, init_effect, follow_beam, "bhvGokuDash")
id_bhvGokuBurst = hook_behavior(nil, OBJ_LIST_DEFAULT, true, init_ball, follow_beam, "bhvGokuBurst")

local function place_dashes(g, o, x, y, z, dx, dz, length, radius, roll, frame)
    local gap = DASH_GAP
    local phase = (frame * DASH_FLOW) % gap
    local width = radius * 0.72
    for i, d in ipairs(g.dashes) do
        local along = phase + (i - 1) * gap
        if goku_alive(d) then
            if along + gap * 0.6 > length then
                obj_scale(d, 0)
            else
                d.oPosX, d.oPosY, d.oPosZ = x + dx * along, y, z + dz * along
                d.oFaceAngleYaw, d.oFaceAngleRoll = o.oFaceAngleYaw, roll
                obj_scale_xyz(d, width / 100, width / 100, gap * 0.64 / 100)
            end
        end
    end
end

local function beam_loop(o)
    local m = owner(o)
    if not m or m.actionState ~= 1 or gGoku[m.playerIndex].beam ~= o then
        obj_mark_for_deletion(o)
        return
    end
    local g = gGoku[m.playerIndex]
    local frame = math.max(THRUST, m.actionTimer - 1)
    local stop = wave_frames(m)
    if frame >= stop then
        g.beam = nil
        obj_mark_for_deletion(o)
        return
    end
    local x, y, z = palms(m, "fire", fire_frame(m, frame))
    local dx, dz = sins(o.oFaceAngleYaw), coss(o.oFaceAngleYaw)
    local q = o.oGokuCharge / KAME_FULL
    local limit = 1400 + 1800 * q

    local ahead = (x - m.pos.x) * dx + (z - m.pos.z) * dz
    local wall = goku_ray_length(x - dx * ahead, y, z - dz * ahead, dx, 0, dz, limit + ahead)
    if wall < ahead then
        x, z = x - dx * (ahead - wall), z - dz * (ahead - wall)
    end
    local reach = math.max(0, wall - ahead)
    local age = frame - THRUST + 1
    local length = math.min(age * math.min(48 + 13 * age, BEAM_SPEED), reach)
    local taper = math.min(1, (stop - frame) / 5)
    local radius = (9 + 15 * q) * taper * (1 + 0.07 * sins(frame * 0x2900))
    o.oPosX, o.oPosY, o.oPosZ = x, y, z
    o.oGokuLength = length
    local cam = gLakituState.pos
    local side = (cam.x - x) * dz - (cam.z - z) * dx
    local roll = atan2s(side, cam.y - y)
    g.beamLength = length

    local headRadius = math.min(radius * 2.1, length / 2)
    local tip = math.max(0, length - headRadius)
    obj_scale_xyz(o, radius / 50, radius / 50, tip / 100)
    place_dashes(g, o, x, y, z, dx, dz, tip, radius, roll, frame)
    local head = g.waveHead
    if goku_alive(head) and head.parentObj == o then
        draw_ball(head, x + dx * tip, y, z + dz * tip, headRadius)
    end
    local tx, tz = x + dx * length, z + dz * length
    if length >= reach and reach < limit then
        if o.oAction == 0 then
            o.oAction = 1
            goku_sound(m, "goku_kame_impact.ogg", 0.65, {x = tx, y = y, z = tz})
            g.burst = spawn_effect(m, id_bhvGokuBurst, E_MODEL_GOKU_BURST, function(b) b.parentObj = o end)
            spawn_non_sync_object(id_bhvMistCircParticleSpawner, E_MODEL_MIST, tx - dx * 20, y, tz - dz * 20, nil)
        end
        if goku_alive(g.burst) then

            local kick = (o.oTimer % 4 < 2) and 1 or 0.78
            draw_ball(g.burst, tx - dx * 8, y, tz - dz * 8, (40 + 44 * q) * kick * taper)
            g.burst.oFaceAngleRoll = o.oTimer * 0x1A00
        end
    end
    if length <= 0 then return end
    if m.playerIndex == 0 then
        goku_attack_segment(x, y, z, tx, y, tz, radius + 4, ATTACK_PUNCH, o.oGokuTag)
    end
    goku_attack_local_player(o, x, y, z, tx, y, tz, radius + 4, q >= 1 and 3 or 2)
end

id_bhvGokuBeam = hook_behavior(nil, OBJ_LIST_DEFAULT, true, init_effect, beam_loop, "bhvGokuBeam")

local function fire_wave(m, g)
    local beam = spawn_effect(m, id_bhvGokuBeam, E_MODEL_GOKU_BEAM, function(o)
        o.oGokuCharge = m.actionArg
        o.oGokuTag = goku_new_tag()
        o.oFaceAngleYaw = m.faceAngle.y
    end)
    g.beam, g.beamLength, g.burst = beam, 0, nil
    g.dashes = {}
    if beam then
        g.waveHead = spawn_effect(m, head_behavior, E_MODEL_GOKU_BALL, function(o) o.parentObj = beam end)
        for i = 1, DASHES do
            g.dashes[i] = spawn_effect(m, id_bhvGokuDash, E_MODEL_GOKU_DASH, function(o)
                o.parentObj = beam
                o.oFaceAngleYaw = m.faceAngle.y
            end)
        end
    end

    local old = g.ball
    g.ball = spawn_effect(m, id_bhvGokuBall, E_MODEL_GOKU_BALL, function(o)
        if goku_alive(old) then
            o.oPosX, o.oPosY, o.oPosZ = old.oPosX, old.oPosY, old.oPosZ
            obj_scale(o, old.header.gfx.scale.x)
        end
    end)
    goku_sound(m, "goku_ha.ogg")
    goku_sound(m, m.actionArg < FULL_BLAST_FROM and "goku_kame_fire_short.ogg" or "goku_kame_fire.ogg", 0.8)
end

local function act_goku_kame(m)
    local g = gGoku[m.playerIndex]
    local air = m.pos.y > m.floorHeight + 4
    local frame = m.actionTimer
    if m.actionState == 0 then
        if g.anim ~= "goku_kame_charge" then
            g.fired = false
            if air then m.vel.y = math.max(-1, math.min(3, m.vel.y)) end
            g.ball = spawn_effect(m, id_bhvGokuBall, E_MODEL_GOKU_BALL)
            g.chant = 1
            g.riseBeat = nil
        end

        local syllable = CHANT[g.chant]
        if syllable and frame >= syllable[1] then
            goku_sound(m, syllable[2])
            g.chant = g.chant + 1
        end
        goku_anim(m, "goku_kame_charge")
        set_anim_to_frame(m, charge_frame(frame))
        m.actionTimer = math.min(frame + 1, KAME_FULL)
        if m.playerIndex == 0 and m.controller.buttonDown & B_BUTTON == 0 and m.actionTimer >= KAME_MIN then
            m.actionArg = m.actionTimer
            m.actionState = 1
            m.actionTimer = 0
        end
    else
        if g.anim ~= "goku_kame_fire" then
            g.fired = false
            g.beam, g.waveHead, g.beamLength = nil, nil, 0
            if g.anim ~= "goku_kame_charge" or not goku_alive(g.ball) then
                g.ball = spawn_effect(m, id_bhvGokuBall, E_MODEL_GOKU_BALL)
            end
        end
        goku_anim(m, "goku_kame_fire")
        set_anim_to_frame(m, fire_frame(m, frame))
        local stop = wave_frames(m)

        if not g.fired and frame >= THRUST and frame < stop then
            g.fired = true

            m.forwardVel = -(air and 5 or 7) - (air and 7 or 11) * m.actionArg / KAME_FULL
            if m.playerIndex == 0 and m.actionArg >= KAME_FULL then
                set_camera_shake_from_hit(SHAKE_SMALL_DAMAGE)
            end
            fire_wave(m, g)
        end

        if not air and frame > THRUST and frame < THRUST + 6 and frame % 2 == 0 then
            m.particleFlags = m.particleFlags | PARTICLE_DUST
        end
        m.actionTimer = frame + 1
        if m.actionTimer >= stop + RECOVER then

            if m.playerIndex == 0 then return set_mario_action(m, air and ACT_FREEFALL or ACT_IDLE, 0) end
            m.actionTimer = stop + RECOVER - 1
        end
    end

    if air then
        m.vel.y = approach_f32(m.vel.y, m.actionState == 0 and -0.65 or -1, 1, 1)
        m.forwardVel = approach_f32(m.forwardVel, 0, 1, 1)
        m.vel.x, m.vel.z = sins(m.faceAngle.y) * m.forwardVel, coss(m.faceAngle.y) * m.forwardVel
        local step = perform_air_step(m, 0)
        if step == AIR_STEP_LANDED then m.vel.y = 0 end
    else
        m.vel.y = 0
        mario_set_forward_vel(m, approach_f32(m.forwardVel, 0, 1.2, 1.2))
        perform_ground_step(m)
    end
    if m.playerIndex == 0 then
        local stickYaw = m.intendedYaw
        if m.intendedMag > 8 and m.actionState == 0 then
            m.faceAngle.y = approach_s32(m.faceAngle.y, stickYaw, 0x400, 0x400)
        end
    end
    return 0
end

hook_mario_action(ACT_GOKU_KAME, {every_frame = act_goku_kame, gravity = function() end})

local FROM = {
    [ACT_PUNCHING] = true, [ACT_MOVE_PUNCHING] = true, [ACT_JUMP_KICK] = true, [ACT_DIVE] = true,
}

function goku_kame_update(m)
    local g = gGoku[m.playerIndex]
    if m.playerIndex ~= 0 then return end
    if m.controller.buttonDown & B_BUTTON ~= 0 then g.bHeld = g.bHeld + 1 else g.bHeld = 0 end
    if g.bHeld >= 10 and FROM[m.action] then
        set_mario_action(m, ACT_GOKU_KAME, 0)
    end
end
