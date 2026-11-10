-- name: Kid Goku check
-- description: Drives Kid Goku through his moves headless and prints [GOKUTEST] lines for scripts/check.mjs.

local function out(s) print("[GOKUTEST] " .. s) end

local input = {buttons = 0, pressed = 0, x = 0, y = 0}
local steps, step, wait = {}, 1, 0
local results = {pass = 0, fail = 0}
local function check(name, ok, detail)
    if ok then results.pass = results.pass + 1 else results.fail = results.fail + 1 end
    out((ok and "PASS " or "FAIL ") .. name .. (detail and (" (" .. detail .. ")") or ""))
end
local trace, traceName = 0, ""
local function trace_for(name, frames) trace, traceName = frames, name end

local cam = nil
local function rec(on) if GOKU_CAPTURE and film_record then film_record(on) end end
local function shoot(angle, dist, height)
    if not GOKU_CAPTURE then return end
    if not cam then camera_freeze(); hud_hide() end
    cam = {angle = angle, dist = dist or 380, height = height or 90}
end
local face, hand, eyes, lastEye, head = nil, nil, nil, nil, nil
local seen_anims, facing = nil, nil
local function anim_name(m) return smlua_anim_util_get_current_animation_name(m.marioObj) end
local function press_a() input.pressed = A_BUTTON; input.buttons = A_BUTTON end
hook_event(HOOK_MARIO_UPDATE, function(m)
    if m.playerIndex == 0 and face then m.marioBodyState.eyeState = face end
    if m.playerIndex == 0 and hand then m.marioBodyState.handState = hand end
end)
hook_event(HOOK_UPDATE, function()
    if not cam then return end
    local m = gMarioStates[0]
    local yaw = m.faceAngle.y + cam.angle
    local l = gLakituState
    local ex, ey, ez = m.pos.x + sins(yaw) * cam.dist, m.pos.y + cam.height, m.pos.z + coss(yaw) * cam.dist
    for _, v in ipairs({l.pos, l.curPos, l.goalPos}) do v.x, v.y, v.z = ex, ey, ez end
    for _, v in ipairs({l.focus, l.curFocus, l.goalFocus}) do v.x, v.y, v.z = m.pos.x, m.pos.y + 75, m.pos.z end
end)
local tick = nil
local function add(f, frames) steps[#steps + 1] = {f = f, frames = frames or 1} end

hook_event(HOOK_BEFORE_MARIO_UPDATE, function(m)
    if m.playerIndex ~= 0 then return end
    local c = m.controller
    c.buttonDown = input.buttons | input.pressed
    c.buttonPressed = input.pressed
    c.stickX, c.stickY = input.x, input.y
    c.stickMag = math.sqrt(input.x * input.x + input.y * input.y)
    local function raw(v) return v == 0 and 0 or v + (v > 0 and 6 or -6) end
    c.rawStickX, c.rawStickY = raw(input.x), raw(input.y)
    input.pressed = 0
end)

local function first(bhv)
    local o = obj_get_first_with_behavior_id(bhv)
    return o
end

local function act() return gMarioStates[0].action end
local heard, zips, lastSaid = {}, 0, nil
local kickHits, skid = 0, nil

local function tail_links()
    local links, o = {}, first(_G.kidGoku.behaviors.tail)
    while o do
        links[#links + 1] = o
        o = obj_get_next_with_same_behavior_id(o)
    end
    return links
end
local function s16(a) return (a + 0x8000) % 0x10000 - 0x8000 end
local G, frame, peak, startX, startZ = nil, 0, 0, 0, 0
local goomba

add(function() warp_to_level(LEVEL_BOB, 1, 1) end, 90)

for _ = 1, 8 do add(function() if get_dialog_id() >= 0 then input.pressed = A_BUTTON end end, 15) end
add(function(m) check("opening dialog closed", get_dialog_id() < 0 and m.freeze == 0) end, 10)
add(function(m)
    G = _G.kidGoku
    check("mod loaded", G ~= nil)
    if not G then return end
    local n = _G.charSelect.character_get_number_from_string("Kid Goku")
    check("listed in Character Select", n ~= nil and n == G.character(), tostring(n))
    _G.charSelect.character_set_current_number(n, 1)
    _G.charSelect.set_menu_open(false)
end, 30)
add(function(m)
    check("menu closed", not _G.charSelect.is_menu_open())
    local np = gNetworkPlayers[0]
    local c = network_player_get_override_palette_color(np, SHIRT)
    out(string.format("INFO palette %s shirt %02x%02x%02x restrict %s", tostring(_G.charSelect.character_get_current_palette_number(0)),
        c.r, c.g, c.b, tostring(gGlobalSyncTable.charSelectRestrictPalettes)))
    check("wears his model", obj_has_model_extended(m.marioObj, G.model) ~= 0)
    check("tail follows him", first(G.behaviors.tail) ~= nil)
end)

add(function(m) eyes = {others = 0, blinks = 0, longest = 0, run = 0} end, 360)
add(function(m)
    local e = eyes
    eyes = nil
    check("idle shows only his relaxed face and its blink", e.others == 0, e.others .. " frames of others")
    check("he blinks now and then", e.blinks >= 1 and e.blinks <= 8, e.blinks .. " in 12 seconds")
    check("a blink is quick", e.longest <= 5, e.longest .. " frames")
    set_mario_action(m, ACT_SLEEPING, 0)
end, 5)
add(function(m)
    check("asleep his eyes are shut, not laughing", lastEye == 10, tostring(lastEye))
    set_mario_action(m, ACT_IDLE, 0)
end)

if not GOKU_CAPTURE then

    add(function(m) head = {last = nil, most = 0, seen = false}; set_mario_action(m, ACT_CROUCHING, 0) end, 30)
    add(function(m)
        local h = head
        head = nil
        check("a change of animation blends", h.seen)
        check("a change of animation doesn't jump", h.most < 13, string.format("%.1f units a frame", h.most))
        check("the blend ends", not G.blending(0))
        out(string.format("INFO crouch head moved %.1f units in a frame at most", h.most))
        set_mario_action(m, ACT_IDLE, 0)
    end, 14)
end

add(function(m) shoot(0, 300, 80); rec(true); tick = function() if cam then cam.angle = cam.angle + 0x400 end end end, 64)

add(function(m) tick = nil; shoot(0, 150, 110) end, 4)
add(function(m) shoot(0x8000, 220, 90) end, 4)

for e = 1, 8 do
    add(function(m) face = e; shoot(0, 150, 70) end, 8)
end
add(function(m) face = nil end, 2)

if GOKU_CAPTURE then
    for e = 9, 17 do
        add(function(m) face = e; shoot(0, 150, 70) end, 8)
    end
    add(function(m) face = nil end, 2)
    for _, h in ipairs({MARIO_HAND_OPEN, MARIO_HAND_PEACE_SIGN}) do
        add(function(m) hand = h; shoot(0x1800, 170, 50) end, 8)
    end
    add(function(m) hand = nil end, 2)
end
add(function(m) rec(false); shoot(0x3000, 420, 110) end)

local function face_open(m)
    local best, bestLen = 0, -1
    for k = 0, 15 do
        local yaw = k * 0x1000
        local dx, dz = sins(yaw), coss(yaw)
        local hit = collision_find_surface_on_ray(m.pos.x, m.pos.y + 70, m.pos.z, dx * 3000, 0, dz * 3000, 3)
        local len = 3000
        if hit and hit.surface then len = math.sqrt((hit.hitPos.x - m.pos.x) ^ 2 + (hit.hitPos.z - m.pos.z) ^ 2) end
        if len > bestLen then best, bestLen = yaw, len end
    end
    m.faceAngle.y = best
    m.intendedYaw = best
    return bestLen
end
add(function(m) out(string.format("INFO open ahead %.0f", face_open(m))) end, 5)

add(function(m) input.pressed = B_BUTTON end, 3)
add(function(m) check("tapped B punches", act() == ACT_PUNCHING, string.format("0x%x", act())) end, 30)

add(function(m) input.buttons = B_BUTTON; input.pressed = B_BUTTON; rec(true) end, 20)
add(function(m) check("held B charges the Kamehameha", act() == G.actions.kame and m.actionState == 0)
    check("charging he's determined", lastEye == MARIO_EYES_LOOK_LEFT, tostring(lastEye))
    local ball = first(G.behaviors.ball)
    check("charge ball shows", ball ~= nil)
end, 50)
add(function(m)
    local ball = first(G.behaviors.ball)
    local side = ball and ((ball.oPosX - m.pos.x) * coss(m.faceAngle.y) - (ball.oPosZ - m.pos.z) * sins(m.faceAngle.y))
    check("charge gathers at his right side", side ~= nil and side < -6, tostring(side))
    input.buttons = 0
end, 2)
add(function(m) check("palms move before the wave", m.actionState == 1 and first(G.behaviors.beam) == nil) end, 5)
add(function(m)
    check("letting go fires", act() == G.actions.kame and m.actionState == 1)
    check("firing, he shouts", lastEye == MARIO_EYES_LOOK_RIGHT, tostring(lastEye))
    local beam = first(G.behaviors.beam)
    check("beam spawns", beam ~= nil)
    if beam then
        local ahead = (beam.oPosX - m.pos.x) * sins(m.faceAngle.y) + (beam.oPosZ - m.pos.z) * coss(m.faceAngle.y)
        check("wave starts at his outstretched hands", ahead > 18 and ahead < 52, tostring(ahead))
    end
end, 12)
add(function(m)
    local len = G.beamLength(0)
    check("beam reaches out", len > 1000, string.format("%.0f", len))
end, 36)
add(function(m)
    rec(false)
    check("back to standing", act() == ACT_IDLE, string.format("0x%x", act()))
    check("charge and wave clear", first(G.behaviors.ball) == nil and first(G.behaviors.beam) == nil
        and first(G.behaviors.dash) == nil and first(G.behaviors.spark) == nil and G.beamLength(0) == 0)
end, 10)

add(function(m) input.buttons = B_BUTTON; input.pressed = B_BUTTON end, 40)
add(function(m)
    local yaw = m.faceAngle.y
    local x, z = m.pos.x + sins(yaw) * 400, m.pos.z + coss(yaw) * 400
    goomba = spawn_sync_object(id_bhvGoomba, E_MODEL_GOOMBA, x, find_floor_height(x, m.pos.y + 200, z), z, nil)
    check("goomba placed", goomba ~= nil)
    input.buttons = 0
end, 40)
add(function(m)
    check("beam defeats the goomba", goomba == nil or goomba.activeFlags == ACTIVE_FLAG_DEACTIVATED or goomba.oAction ~= 0,
        goomba and ("action " .. goomba.oAction) or "")
end, 20)

local openYaw
add(function(m)
    openYaw = m.faceAngle.y
    local nearest = 2200
    for i = 0, 31 do
        local yaw = i * 0x800
        local hit = collision_find_surface_on_ray(m.pos.x, m.pos.y + 52, m.pos.z, sins(yaw) * nearest, 0, coss(yaw) * nearest, 3)
        if hit.surface then
            local d = math.sqrt((hit.hitPos.x - m.pos.x)^2 + (hit.hitPos.z - m.pos.z)^2)
            if d > 90 then nearest, m.faceAngle.y = d, yaw end
        end
    end
    check("a wall is in range", nearest < 2200)
    input.pressed, input.buttons = B_BUTTON, B_BUTTON
end, 122)
add(function(m)
    check("full charge waits for B release", act() == G.actions.kame and m.actionState == 0 and first(G.behaviors.beam) == nil)
    input.buttons = 0
end, 24)
add(function(m)
    local b = first(G.behaviors.beam)
    local hit = b and collision_find_surface_on_ray(b.oPosX, b.oPosY, b.oPosZ, sins(m.faceAngle.y) * 3200, 0,
        coss(m.faceAngle.y) * 3200, 3)
    local distance = hit and hit.surface and math.sqrt((hit.hitPos.x - b.oPosX)^2 + (hit.hitPos.z - b.oPosZ)^2)
    check("wave stops at the wall", distance and math.abs(G.beamLength(0) - distance) < 2, tostring(distance))
end, 42)
add(function(m) m.faceAngle.y = openYaw; input.pressed = A_BUTTON end, 4)
add(function(m) input.buttons, input.pressed = B_BUTTON, B_BUTTON end, 32)
add(function(m)
    check("charges in the air", act() == G.actions.kame and m.pos.y > m.floorHeight + 8, string.format("action %x, height %.0f", m.action, m.pos.y - m.floorHeight))
    input.buttons = 0
end, 9)
add(function(m)
    check("fires in the air", G.beamLength(0) > 0 and m.pos.y > m.floorHeight + 4)
    set_mario_action(m, ACT_FREEFALL, 0)
end, 4)
add(function(m)
    check("interrupting the cast clears its effects", first(G.behaviors.beam) == nil and first(G.behaviors.ball) == nil)
end, 80)

add(function(m) input.pressed = X_BUTTON end, 6)
add(function(m) check("X does nothing on the ground", act() == ACT_IDLE, string.format("0x%x", act())) end)
add(function(m) input.pressed = A_BUTTON; input.buttons = A_BUTTON end, 8)
add(function(m)
    check("jumping he's happy, not blank", lastEye == MARIO_EYES_LOOK_DOWN, tostring(lastEye))
    input.buttons = 0; input.pressed = X_BUTTON
end, 4)
add(function(m) check("X does nothing in the air", act() == ACT_JUMP, string.format("0x%x", act())) end, 60)

add(function(m) face_open(m); input.x, input.y = 0, 36 end, 45)
add(function(m)
    check("walking he smiles, not blank", m.action == ACT_WALKING and lastEye == 11, string.format("0x%x, eye %s", m.action, tostring(lastEye)))
end)

add(function(m) input.x, input.y = 0, 0; set_mario_action(m, ACT_IDLE, 0) end, 60)
add(function(m)
    local links = tail_links()
    check("the tail has thirteen links", #links == 13, tostring(#links))
    local gap, low, high = 0, 0, 0
    for j, o in ipairs(links) do
        local a = o.header.gfx
        local up = -s16(a.angle.x)
        low, high = math.min(low, up), math.max(high, up)
        if links[j + 1] then
            local reach = 8.6 * 9 / 13 * m.marioObj.header.gfx.scale.y
            local b = links[j + 1].header.gfx
            local dx = a.pos.x + sins(a.angle.y) * coss(up) * reach - b.pos.x
            local dy = a.pos.y + sins(up) * reach - b.pos.y
            local dz = a.pos.z + coss(a.angle.y) * coss(up) * reach - b.pos.z
            gap = math.max(gap, math.sqrt(dx * dx + dy * dy + dz * dz))
        end
    end
    check("the tail's links stay joined", gap < 1.5, string.format("%.1f", gap))
    check("resting, the tail curves", low < -0x500 and high > 0x1800, string.format("0x%x to 0x%x", low & 0xffff, high))
end)

add(function(m) face_open(m); input.x, input.y = 0, 64; shoot(0x4000, 420, 100); rec(true) end, 60)
add(function(m) startX, startZ = m.pos.x, m.pos.z end, 10)
add(function(m)
    local d = math.sqrt((m.pos.x - startX) ^ 2 + (m.pos.z - startZ) ^ 2) / 10
    rec(false)
    check("runs faster than Mario", m.action == ACT_WALKING and d > 33, string.format("%.1f units a frame", d))

    local root = first(G.behaviors.tail)
    local tx, tz = root.header.gfx.pos.x - m.pos.x, root.header.gfx.pos.z - m.pos.z
    check("the tail stays on him at a run", math.sqrt(tx * tx + tz * tz) < 50, string.format("%.0f", math.sqrt(tx * tx + tz * tz)))
    local links = tail_links()
    local tip = links[#links].header.gfx
    local behind = -((tip.pos.x - root.header.gfx.pos.x) * sins(m.faceAngle.y) + (tip.pos.z - root.header.gfx.pos.z) * coss(m.faceAngle.y))
    check("at a run the tail streams behind him", behind > 45, string.format("%.0f", behind))
    check("running he grins, not blank", lastEye == MARIO_EYES_LOOK_DOWN, tostring(lastEye))

    local body = m.marioBodyState

    check("running he looks ahead, not at the ground", body.allowPartRotation ~= 0 and body.torsoAngle.x > 0x1000
        and math.abs(body.headAngle.x + body.torsoAngle.x) <= 0x400,
        string.format("torso %d head %d", body.torsoAngle.x, body.headAngle.x))
    input.x, input.y = 0, 0
end, 8)
add(function(m) check("a face outlasts a stop", lastEye ~= MARIO_EYES_OPEN, tostring(lastEye)) end, 70)
add(function(m)
    check("stopped he rests", lastEye == MARIO_EYES_OPEN or lastEye == 9 or lastEye == 10, tostring(lastEye))
    check("stopped his head is his own again", m.marioBodyState.allowPartRotation == 0)
end)

if not GOKU_CAPTURE then
    local function steer(m, yaw, mag)
        local a = yaw - m.area.camera.yaw
        input.x, input.y = math.floor(mag * sins(a)), math.floor(-mag * coss(a))
    end
    local along = 0
    add(function(m) along = face_open(m); steer(m, along, 64) end, 36)
    add(function(m)
        head = {last = nil, most = 0, seen = false, relative = true, acts = {}}
        facing = {most = 0}
        steer(m, along + 0x8000, 64)
    end, 50)
    add(function(m)
        local h = head
        head = nil
        check("he turns around", h.acts[ACT_FINISH_TURNING_AROUND] == true)
        check("turning around doesn't snap", h.most < 16, string.format("%.1f units a frame", h.most))
        check("turning around, his body comes round smoothly", facing.most < 0x2000, string.format("0x%x a frame", facing.most))
        facing = nil
        input.x, input.y = 0, 0
    end, 40)

    add(function(m) steer(m, along, 64) end, 36)
    add(function(m)
        head = {last = nil, most = 0, seen = false, relative = true, acts = {}, jump_on = ACT_TURNING_AROUND}
        facing = {most = 0}
        steer(m, along + 0x8000, 64)
    end, 64)
    add(function(m)
        local h = head
        head = nil
        input.buttons, input.x, input.y = 0, 0, 0
        check("he side flips", h.acts[ACT_SIDE_FLIP] == true)
        check("he lands the side flip", h.acts[ACT_SIDE_FLIP_LAND] == true)
        check("side flipping, his body comes round smoothly", facing.most < 0x2000, string.format("0x%x a frame", facing.most))
        facing = nil
        set_mario_action(m, ACT_IDLE, 0)
    end, 20)

    add(function(m) set_mario_action(m, ACT_IDLE, 0); m.actionTimer = 1 end, 4)
    add(function(m)
        check("standing about he puts his hands on his hips", anim_name(m) == "goku_hips", tostring(anim_name(m)))
        seen_anims = {}
        set_mario_action(m, ACT_START_SLEEPING, 0)
    end, 245)
    add(function(m)
        local s = seen_anims
        seen_anims = nil
        for _, name in ipairs({"goku_tired_50", "goku_scratch_67", "goku_yawn_59", "goku_sit_down_64"}) do
            check("nodding off plays " .. name, s[name] == true)
        end
        set_mario_action(m, ACT_SLEEPING, 0)
        m.actionState = 2
    end, 4)
    add(function(m)
        check("asleep he lies on his back", anim_name(m) == "goku_sleep_back_50", tostring(anim_name(m)))
        set_mario_action(m, ACT_START_SLEEPING, 0)
        m.actionState = 2
    end, 5)
    add(function(m)
        check("yawning his eyes are shut and his mouth wide", lastEye == MARIO_EYES_CLOSED, tostring(lastEye))
        set_mario_action(m, ACT_IDLE, 0)
    end, 10)

    local woke, wraps
    add(function(m) set_mario_action(m, ACT_SLEEPING, 0) end, 30)
    add(function(m)
        woke = {}
        tick = function(m)
            if m.action == ACT_WAKING_UP then woke[#woke + 1] = m.marioObj.header.gfx.animInfo.animFrame end
        end
        input.x, input.y = 0, 40
    end, 1)
    add(function() input.x, input.y = 0, 0 end, 30)
    add(function(m)
        tick = nil
        check("waking up he plays all of it and ends as he stands", #woke > 0 and woke[1] <= 7 and woke[#woke] >= 24,
            string.format("%s to %s", tostring(woke[1]), tostring(woke[#woke])))
        set_mario_action(m, ACT_IDLE, 0)
    end, 10)

    add(function(m)
        wraps = {}
        local age, last = 0, nil
        tick = function(m)
            age = age + 1
            local info = m.marioObj.header.gfx.animInfo
            if info.animID ~= CHAR_ANIM_TIPTOE then return end
            local f = info.animFrame
            if last and f < last then wraps[#wraps + 1] = age end
            last = f
        end
        local a = 0x4000 - m.area.camera.yaw
        input.x, input.y = math.floor(22 * sins(a)), math.floor(-22 * coss(a))
    end, 130)
    add(function(m)
        tick = nil
        input.x, input.y = 0, 0
        local cycle = #wraps >= 2 and wraps[2] - wraps[1] or 0
        check("tiptoeing he keeps the pace of his first steps", cycle >= 27 and cycle <= 31, tostring(cycle))
        set_mario_action(m, ACT_IDLE, 0)
    end, 10)
end

add(function(m) face_open(m); set_mario_action(m, ACT_IDLE, 0); input.pressed = B_BUTTON end, 9)
add(function(m) input.pressed = B_BUTTON end, 9)
add(function(m) input.pressed = B_BUTTON end, 40)
add(function(m)
    check("Rock, Scissors and Paper only whoosh when they hit nothing", heard["goku_swing.ogg"] and heard["goku_swing_big.ogg"]
        and not heard["goku_punch.ogg"] and not heard["goku_heavy_punch.ogg"])
    set_mario_action(m, ACT_JUMP_KICK, 0)
end, 30)
add(function(m) check("a jump kick that hits nothing makes no impact", heard["goku_swing_big.ogg"] and not heard["goku_heavy_kick.ogg"])
    set_mario_action(m, ACT_SLIDE_KICK, 0) end, 30)
add(function(m) check("a slide kick shouts and makes no impact", heard["goku_shout_arya.ogg"] and not heard["goku_heavy_kick.ogg"])
    set_mario_action(m, ACT_GROUND_POUND_LAND, 0) end, 30)
add(function(m) check("a ground pound lands a heavy blow", heard["goku_heavy_punch.ogg"]); heard["goku_heavy_punch.ogg"] = nil
    set_mario_action(m, ACT_IDLE, 0) end, 20)

local function land_blow(m) play_sound(SOUND_ACTION_HIT_2, m.marioObj.header.gfx.cameraToObject) end
add(function(m) set_mario_action(m, ACT_IDLE, 0); input.pressed = B_BUTTON end, 4)
add(land_blow, 12)
add(function(m)
    check("a punch that lands is heard", heard["goku_punch.ogg"])
    check("a blow that lands shows on his face", lastEye == G.faces.grin, tostring(lastEye))
    set_mario_action(m, ACT_JUMP_KICK, 0)
end, 3)
add(land_blow, 2)
add(function(m) check("a kick that lands is heard", heard["goku_heavy_kick.ogg"]); set_mario_action(m, ACT_IDLE, 0) end, 40)

local combo = {}
hook_event(HOOK_BEFORE_MARIO_UPDATE, function(m)
    if m.playerIndex ~= 0 or m.action ~= ACT_MOVE_PUNCHING then return end
    if m.actionArg == 3 then combo.second = true end

    if m.actionArg == 6 and combo.third == nil then combo.third = m.flags & MARIO_ACTION_SOUND_PLAYED == 0 end
end)
add(function(m) set_mario_action(m, ACT_IDLE, 0); combo = {}; input.pressed = B_BUTTON end, 5)
add(function(m) m.action = ACT_MOVE_PUNCHING; m.forwardVel = -48 end, 4)
add(function(m) input.pressed = B_BUTTON end, 9)
add(function(m) input.pressed = B_BUTTON end, 40)
add(function(m)
    check("a combo that lands still shouts Scissors and Paper", combo.second == true and combo.third == true,
        string.format("second %s third %s", tostring(combo.second), tostring(combo.third)))
    set_mario_action(m, ACT_IDLE, 0)
end, 3)
add(function(m) combo = {}; set_mario_action(m, ACT_MOVE_PUNCHING, 0) end, 4)
add(function(m) input.pressed = B_BUTTON end, 9)
add(function(m) input.pressed = B_BUTTON end, 40)
add(function(m)
    check("his walking kicks shout neither", not combo.second and combo.third ~= true,
        string.format("second %s third %s", tostring(combo.second), tostring(combo.third)))
    set_mario_action(m, ACT_IDLE, 0)
end, 4)

add(function(m)
    m.pos.y = m.pos.y + 400
    m.vel.y = 0
    set_mario_action(m, ACT_FREEFALL, 0)
end, 3)
add(function(m) play_sound(SOUND_ACTION_BOUNCE_OFF_OBJECT, m.marioObj.header.gfx.cameraToObject) end, 3)
add(function(m)
    check("with no enemy there's no stomp", G.stompLeft(0) == 0 and anim_name(m) ~= "goku_stomp_enemy", tostring(anim_name(m)))
    set_mario_action(m, ACT_IDLE, 0)
end, 10)
add(function(m) set_mario_action(m, ACT_BACKWARD_GROUND_KB, 0) end, 4)
add(function(m) check("knocked back it shows on his face", lastEye == G.faces.hit, tostring(lastEye)); set_mario_action(m, ACT_IDLE, 0) end, 20)

local function hurt_clip(m) return _G.charSelect.character_get_voice(m)[CHAR_SOUND_OOOF].filepath end
add(function(m)
    check("his voice starts in Japanese", hurt_clip(m) == "goku_hurt.ogg", hurt_clip(m))
    G.setEnglish(true)
    set_mario_action(m, ACT_SLIDE_KICK, 0)
end, 20)
add(function(m)
    check("English Voice swaps his voice table", hurt_clip(m) == "goku_en_hurt.ogg", hurt_clip(m))
    check("English Voice swaps his own shouts", heard["goku_en_shout_arya.ogg"])
    G.setEnglish(false)
    check("his voice goes back to Japanese", hurt_clip(m) == "goku_hurt.ogg", hurt_clip(m))
    set_mario_action(m, ACT_IDLE, 0)
end, 10)

add(function(m) face_open(m); m.forwardVel = 0; kickHits = 0; set_mario_action(m, ACT_JUMP_KICK, 0) end, 3)
add(function(m)
    check("B in the air is his flying kick", anim_name(m) == "goku_kick_32", tostring(anim_name(m)))
    check("the kick carries him forward", m.forwardVel >= 20, string.format("%.0f", m.forwardVel))
    check("he kicks with his fight face", lastEye == G.faces.grit, tostring(lastEye))
end, 50)
add(function(m)
    check("his leg hits for as long as it's out", kickHits > 8, tostring(kickHits))
    set_mario_action(m, ACT_IDLE, 0)
    face_open(m)
    input.x, input.y = 0, 26
end, 24)
add(function(m) input.pressed = B_BUTTON end, 3)
add(function(m)
    check("walking, B is a side kick", act() == ACT_MOVE_PUNCHING and (anim_name(m) or ""):find("side_kick") ~= nil,
        string.format("0x%x %s", act(), tostring(anim_name(m))))
    check("the side kick raises no dust", m.marioObj.oActiveParticleFlags & ACTIVE_PARTICLE_DUST ~= 0)
    input.x, input.y = 0, 0
end, 40)

local swelled, watchSwell = false, false
hook_event(HOOK_BEFORE_MARIO_UPDATE, function(m)
    if watchSwell and m.playerIndex == 0 and m.marioBodyState.punchState ~= 0 then swelled = true end
end)
add(function(m)
    set_mario_action(m, ACT_IDLE, 0)
    input.pressed = B_BUTTON
    watchSwell = true
end, 34)
add(function(m)
    watchSwell = false
    check("no fist swells on a punch", not swelled)
    check("after a punch he stays in his stance", anim_name(m) == "goku_fight_ready", tostring(anim_name(m)))
    check("in his stance he has his fight face", lastEye == G.faces.fierce, tostring(lastEye))
end, 90)
add(function(m)
    check("then he relaxes", anim_name(m) ~= "goku_fight_ready", tostring(anim_name(m)))
    check("after the kick the dust works again", m.marioObj.oActiveParticleFlags & ACTIVE_PARTICLE_DUST == 0)
    face_open(m)
    input.x, input.y = 0, 64
end, 40)
add(function(m)
    input.pressed = B_BUTTON
    skid = nil
    tick = function(m) if m.action == ACT_DIVE_SLIDE then skid = anim_name(m) end end
end, 4)
add(function(m)
    check("at a run, B lunges boot first", act() == ACT_DIVE and anim_name(m) == "goku_lunge_20",
        string.format("0x%x %s", act(), tostring(anim_name(m))))
    check("he yells as he lunges", lastEye == G.faces.yell, tostring(lastEye))
    input.x, input.y = 0, 0
end, 40)
add(function(m)
    tick = nil
    check("the lunge lands him on his feet", skid == "goku_lunge_skid", tostring(skid))
    set_mario_action(m, ACT_IDLE, 0)
end, 10)

add(function(m) face_open(m); input.pressed = Y_BUTTON; shoot(0x3000, 600, 200); rec(true) end, 5)

function trail_links()
    local links, o = {}, obj_get_first_with_behavior_id(G.behaviors.trail)
    while o do
        if o.header.gfx.node.flags & GRAPH_RENDER_INVISIBLE == 0 then links[#links + 1] = o.header.gfx end
        o = obj_get_next_with_same_behavior_id(o)
    end
    local function far_end(g)
        local reach = g.scale.z * 100
        return g.pos.x + sins(g.angle.y) * coss(g.angle.x) * reach, g.pos.y - sins(g.angle.x) * reach, g.pos.z + coss(g.angle.y) * coss(g.angle.x) * reach
    end
    local gaps, long = {}, 0
    for _, g in ipairs(links) do
        long = long + g.scale.z * 100
        local x, y, z = far_end(g)
        local near = 1e9
        for _, other in ipairs(links) do
            if other ~= g then near = math.min(near, math.sqrt((other.pos.x - x) ^ 2 + (other.pos.y - y) ^ 2 + (other.pos.z - z) ^ 2)) end
        end
        gaps[#gaps + 1] = near
    end

    table.sort(gaps)
    local apart = #gaps > 1 and gaps[#gaps - 1] or 0
    return #links, apart, long
end

add(function(m) check("Y calls the Nimbus", act() == G.actions.nimbusCall)
    check("cloud spawns", first(G.behaviors.nimbus) ~= nil) end, 22)
add(function(m)
    local c = first(G.behaviors.nimbus)
    local d = math.sqrt((c.oPosX - m.pos.x) ^ 2 + (c.oPosZ - m.pos.z) ^ 2)
    check("the cloud stops beside him, not in him", d > 150 and d < 260, string.format("%.0f", d))
end, 20)
add(function(m)
    check("rides the Nimbus", act() == G.actions.nimbus, string.format("0x%x", act()))
    head = {most = 0, relative = true, only = G.actions.nimbus}
end, 60)
add(function(m)
    check("on the Nimbus he stands", anim_name(m) == "goku_nimbus_stand", tostring(anim_name(m)))
    check("hovering, the cloud draws no trail", trail_links() == 0, tostring(trail_links()))
    local c = first(G.behaviors.nimbus)
    local feet = m.marioObj.header.gfx.pos
    check("the cloud stays under his feet", math.abs(feet.y - c.oPosY - 36) < 1 and math.abs(feet.x - c.oPosX) < 12
        and math.abs(feet.z - c.oPosZ) < 12, string.format("%.1f, %.1f, %.1f", feet.x - c.oPosX, feet.y - c.oPosY, feet.z - c.oPosZ))
end, 60)
add(function(m) check("left hovering he sits", anim_name(m) == "goku_nimbus_ride", tostring(anim_name(m))) end, 200)
add(function(m)
    check("then he lies back", anim_name(m) == "goku_nimbus_lie", tostring(anim_name(m)))
    check("standing, sitting and lying back flow together", head.most < 10, string.format("%.1f units a frame", head.most))
    head = nil
    peak = m.pos.y
    input.buttons = A_BUTTON; trace_for("ride", 12)
end, 15)
add(function(m) out(string.format("INFO nimbus action 0x%x y %.0f vy %.0f down %x", act(), m.pos.y, m.vel.y, m.controller.buttonDown)) end, 30)
add(function(m)
    check("A climbs", m.pos.y > peak + 300, string.format("%.0f", m.pos.y - peak))
    input.buttons = 0
    input.x, input.y = 0, 64
    head = {most = 0, relative = true, only = G.actions.nimbus}
end, 40)
add(function(m)
    rec(false)
    check("the cloud is heard coming and setting off", zips >= 2, tostring(zips))
    check("flying he crouches into the wind", anim_name(m) == "goku_nimbus_fly", tostring(anim_name(m)))
    local shown, apart, long = trail_links()
    check("flying, the cloud draws its trail behind it", shown >= 12 and long > 600, string.format("%d links, %.0f long", shown, long))
    check("the trail's links run into each other", apart < 2, string.format("%.1f apart at most", apart))
    check("flying he leans forward", m.marioObj.header.gfx.angle.x > 0x200, string.format("0x%x", m.marioObj.header.gfx.angle.x))
    check("he sets off from a stand smoothly", head.most < 10, string.format("%.1f units a frame", head.most))
    head = nil
    input.x, input.y = 0, 0
    input.pressed = Y_BUTTON
end, 5)
add(function(m) check("Y gets off", act() == ACT_FREEFALL, string.format("0x%x", act())) end, 90)
add(function(m) check("back down", m.action & ACT_FLAG_AIR == 0, string.format("0x%x", act())); input.pressed = Y_BUTTON end, 4)
add(function(m)
    check("Y calls it again once he's off it", act() == G.actions.nimbusCall, string.format("0x%x", act()))
    set_mario_action(m, ACT_IDLE, 0)
end, 20)

add(function(m) m.pos.y = m.pos.y + 500; set_mario_action(m, ACT_TWIRLING, 0) end, 10)
add(function(m)
    check("twirling he flings his arms out", act() == ACT_TWIRLING and anim_name(m) == "goku_twirl_1",
        string.format("0x%x %s", act(), tostring(anim_name(m))))
end, 80)
local carried = {}
local wingCap = nil
add(function(m)
    check("he lands out of the twirl", m.action & ACT_FLAG_AIR == 0, string.format("0x%x", act()))
    set_mario_action(m, ACT_HOLD_JUMP, 0)
    tick = function(m) carried[anim_name(m) or ""] = true end
end, 60)
add(function(m)
    tick = nil
    local seen = {}
    for name in pairs(carried) do seen[#seen + 1] = name end
    check("carrying, he jumps with his hands on it", carried.goku_hold_jump_10, table.concat(seen, " "))
    check("and lands with them on it", carried.goku_hold_land_19, table.concat(seen, " "))
    set_mario_action(m, ACT_IDLE, 0)
end, 10)

add(function(m)
    m.pos.y = m.pos.y + 1500
    m.flags = m.flags | MARIO_WING_CAP
    m.capTimer = 900
    play_cap_music((4 << 8) | SEQ_EVENT_POWERUP)
    set_mario_action(m, ACT_FLYING_TRIPLE_JUMP, 0)
    input.buttons = A_BUTTON
end, 8)
add(function(m)
    check("with the wing cap, the third jump calls the Nimbus", act() == ACT_FLYING_TRIPLE_JUMP and anim_name(m) == "goku_nimbus_call"
        and first(G.behaviors.nimbus) ~= nil and G.played(0, "goku_lets_go.ogg") >= 2,
        string.format("0x%x %s %s", act(), tostring(anim_name(m)), tostring(G.lastSound(0))))
    input.buttons = 0
end, 70)
add(function(m)
    local cloud = first(G.behaviors.nimbus)
    check("then he flies the game's flight", act() == ACT_FLYING, string.format("0x%x", act()))
    check("crouched on the cloud", anim_name(m) == "goku_nimbus_fly", tostring(anim_name(m)))
    local off = cloud and math.sqrt((cloud.oPosX - m.pos.x) ^ 2 + (cloud.oPosY - m.pos.y + 36) ^ 2 + (cloud.oPosZ - m.pos.z) ^ 2) or -1

    check("which carries him", cloud ~= nil and cloud.oAction == 2 and off < 45, string.format("action %s, %.0f from his feet", cloud and cloud.oAction, off))
    local ball = first(G.behaviors.carried)
    local hand = m.marioBodyState.animPartsPos[MARIO_ANIM_PART_LEFT_HAND + 1]
    local reach = ball and math.sqrt((ball.header.gfx.pos.x - hand.x) ^ 2 + (ball.header.gfx.pos.y - hand.y) ^ 2 + (ball.header.gfx.pos.z - hand.z) ^ 2) or -1
    check("he carries the four-star ball in his left hand", ball ~= nil and obj_has_model_extended(ball, G.dragonBall) ~= 0 and reach < 20,
        string.format("%.0f from his wrist", reach))
    local on, swapped = G.wingSong()
    check("his song plays", on, tostring(on))
    check("in place of the cap's tune", swapped, tostring(swapped))
    m.flags = m.flags & ~MARIO_WING_CAP
    m.capTimer = 0
end, 12)
add(function(m)
    local cloud = first(G.behaviors.nimbus)
    check("the cap gone, he drops and the cloud flies off", act() ~= ACT_FLYING and (cloud == nil or cloud.oAction == 3),
        string.format("0x%x cloud %s", act(), cloud and cloud.oAction))
    check("and the song ends", not G.wingSong())
    check("and the ball is gone from his hand", first(G.behaviors.carried) == nil)
    local cap = spawn_non_sync_object(id_bhvWingCap, E_MODEL_MARIOS_WING_CAP, m.pos.x + 300, m.floorHeight + 60, m.pos.z, nil)
    wingCap = cap
    stop_cap_music()
    m.pos.y = m.floorHeight
    set_mario_action(m, ACT_IDLE, 0)
end, 20)
add(function(m)
    check("a wing cap in the level is a Dragon Ball to him", wingCap ~= nil and obj_has_model_extended(wingCap, G.dragonBall) ~= 0,
        wingCap and string.format("model %s ball %s active %s behavior %s/%s", tostring(obj_get_model_id_extended(wingCap)), tostring(G.dragonBall),
            tostring(wingCap.activeFlags), tostring(get_id_from_behavior(wingCap.behavior)), tostring(id_bhvWingCap)) or "no cap")
    if wingCap then obj_mark_for_deletion(wingCap) end
end, 4)

add(function(m)
    m.flags = m.flags | MARIO_WING_CAP
    m.capTimer = 900
    play_cap_music((4 << 8) | SEQ_EVENT_POWERUP)
end, 12)
add(function(m)
    check("his song plays with the cap on again", (G.wingSong()))
    _G.charSelect.character_set_current_number(_G.charSelect.character_get_number_from_string("Mario") or 1, 1)
end, 30)
add(function(m)
    check("he has turned into Mario", obj_has_model_extended(m.marioObj, G.model) == 0)
    check("and his song stops with him", not G.wingSong())
    m.flags = m.flags & ~MARIO_WING_CAP
    m.capTimer = 0
    stop_cap_music()
    _G.charSelect.character_set_current_number(G.character(), 1)
end, 30)
add(function(m)
    check("he is Kid Goku again", obj_has_model_extended(m.marioObj, G.model) ~= 0)
    check("with no song left playing", not G.wingSong())
end, 4)

add(function() warp_to_level(LEVEL_CASTLE_GROUNDS, 1, 1) end, 90)
add(function(m)
    local t = G.tail(0)
    check("he keeps his tail through a level change", t ~= nil and get_id_from_behavior(t.behavior) == G.behaviors.tail)
    local dx, dz = t.header.gfx.pos.x - m.pos.x, t.header.gfx.pos.z - m.pos.z
    check("the new tail is on him", math.sqrt(dx * dx + dz * dz) < 34, string.format("%.0f", math.sqrt(dx * dx + dz * dz)))
end)

add(function() warp_to_level(LEVEL_CASTLE, 1, 0) end, 120)
for _ = 1, 4 do add(function() if get_dialog_id() >= 0 then input.pressed = A_BUTTON end end, 15) end
local door, through = nil, nil
local function go_through(name, start, action, arg, frames, far)
    add(function(m)
        if not door then
            local o = obj_get_first_with_behavior_id(id_bhvDoor)
            while o and (o.oBehParams >> 24) & 0xFF ~= 0 do o = obj_get_next_with_same_behavior_id(o) end
            door = o
        end
        check("a door to " .. name, door ~= nil)
        if not door then return end
        m.pos.x, m.pos.y, m.pos.z = door.oPosX + sins(door.oMoveAngleYaw) * start, door.oPosY, door.oPosZ + coss(door.oMoveAngleYaw) * start
        m.vel.x, m.vel.y, m.vel.z, m.forwardVel = 0, 0, 0, 0
        m.interactObj, m.usedObj = door, door
        through = {door = door, last = nil, most = 0, along = start}
        set_mario_action(m, action, arg)
    end, frames)
    add(function(m)
        local t = through
        through = nil
        if not t then return end
        check(name .. ": out the far side", t.along * far > 250, string.format("%.0f", t.along))
        check(name .. ": a walk, not a teleport", t.most < 14, string.format("%.1f units a frame", t.most))
        set_mario_action(m, ACT_IDLE, 0)
    end, 10)
end
go_through("push", 95, ACT_PUSHING_DOOR, 2, 48, -1)
go_through("pull", -109, ACT_PULLING_DOOR, 1, 58, 1)

add(function(m)
    for _, file in ipairs({"goku_leap.ogg", "goku_leap_big.ogg", "goku_land_tap.ogg", "goku_kame_rise1.ogg", "goku_kame_rise6.ogg",
            "goku_kame_fire.ogg", "goku_kame_fire_short.ogg"}) do
        check("he played " .. file, heard[file] == true)
    end
    out(string.format("DONE %d passed, %d failed", results.pass, results.fail))
end)

hook_event(HOOK_UPDATE, function()
    if facing then
        local yaw = G.bodyYaw(gMarioStates[0])
        if facing.last then facing.most = math.max(facing.most, math.abs(((yaw - facing.last + 0x8000) % 0x10000) - 0x8000)) end
        facing.last = yaw
    end
    if seen_anims then
        local name = anim_name(gMarioStates[0])
        if name then seen_anims[name] = true end
    end
    if through then
        local m = gMarioStates[0]
        local d = through.door
        through.along = (m.pos.x - d.oPosX) * sins(d.oMoveAngleYaw) + (m.pos.z - d.oPosZ) * coss(d.oMoveAngleYaw)
        if through.last and (m.action == ACT_PUSHING_DOOR or m.action == ACT_PULLING_DOOR) then
            through.most = math.max(through.most, math.abs(through.along - through.last))
        end
        through.last = through.along
    end
    if gMarioStates[0].flags & MARIO_KICKING ~= 0 and act() == ACT_JUMP_KICK then kickHits = kickHits + 1 end
    if head then
        local m = gMarioStates[0]
        local p = m.marioBodyState.headPos
        if head.acts then head.acts[m.action] = true end
        if head.jump_on == m.action then head.jump_on = nil; press_a() end

        local bx, by, bz = 0, 0, 0
        local starting = false
        if head.relative then
            local at = m.marioObj.header.gfx.pos
            starting = not head.at
            if head.at then bx, by, bz = head.at.x, head.at.y, head.at.z end
            head.at = {x = at.x, y = at.y, z = at.z}
        end
        if head.last and (not head.only or m.action == head.only) then
            local dx, dy, dz = p.x - bx - head.last.x, p.y - by - head.last.y, p.z - bz - head.last.z
            local d = math.sqrt(dx * dx + dy * dy + dz * dz)
            head.most = math.max(head.most, d)
        end
        if not starting then head.last = {x = p.x - bx, y = p.y - by, z = p.z - bz} end
        head.seen = head.seen or _G.kidGoku.blending(0)
    end
    local state = gMarioStates[0].marioBodyState.eyeState
    lastEye = state
    if not eyes then return end
    if state == MARIO_EYES_OPEN then
        eyes.run = 0
    elseif state == 9 or state == 10 then
        if eyes.run == 0 then eyes.blinks = eyes.blinks + 1 end
        eyes.run = eyes.run + 1
        eyes.longest = math.max(eyes.longest, eyes.run)
    else
        eyes.others = eyes.others + 1
    end
end)

hook_event(HOOK_MARIO_UPDATE, function(m)
    if m.playerIndex ~= 0 then return end
    if G then
        local said = G.lastSound(0) or ""
        heard[said] = true
        zips = G.played(0, "goku_nimbus.ogg")
    end
    if tick then tick(m) end
    if trace > 0 then
        trace = trace - 1
        local b = obj_get_first_with_behavior_id(G.behaviors.beam)
        local yaw = m.faceAngle.y
        local hit = collision_find_surface_on_ray(m.pos.x + sins(yaw) * 70, m.pos.y + 70, m.pos.z + coss(yaw) * 70, sins(yaw) * 3000, 0, coss(yaw) * 3000, 3)
        local rl = hit.surface and math.sqrt((hit.hitPos.x - m.pos.x) ^ 2 + (hit.hitPos.z - m.pos.z) ^ 2) or -1
        local by = b and string.format("%x/%x ray %.0f", b.oFaceAngleYaw & 0xffff, yaw & 0xffff, rl) or ""
        out(string.format("TRACE %s %s action 0x%x st %d t %d y %.0f vy %.1f fv %.1f down %x beamZ %s", traceName, by, m.action,
            m.actionState, m.actionTimer, m.pos.y, m.vel.y, m.forwardVel, m.controller.buttonDown,
            b and string.format("%.2f", b.header.gfx.scale.z) or "-"))
    end
    frame = frame + 1
    if frame % 30 == 0 then out("FRAME " .. frame) end
    if step > #steps then return end
    if wait > 0 then wait = wait - 1; return end
    local s = steps[step]
    step = step + 1
    local ok, err = pcall(s.f, m)
    if not ok then check("step " .. (step - 1), false, tostring(err)) end
    wait = s.frames - 1
end)
