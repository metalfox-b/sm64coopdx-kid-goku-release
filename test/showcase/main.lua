-- name: Kid Goku showcase
-- description: Plays each of Kid Goku's moves once on the game's own camera with the HUD hidden, recording a clip of

local function out(s) print("[GOKUTEST] " .. s) end

local input = {buttons = 0, pressed = 0, x = 0, y = 0}
local steps, step, wait = {}, 1, 0
local recording, recorded, clip = false, 0, nil
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

local function start(name)
    clip = name
    if film_record then film_record(true) end
    recording = true
    out(string.format("CLIP %s %d", name, recorded))
    out(string.format("ROLL %d %d", get_global_timer(), recorded))
end
local function stop()
    if film_record then film_record(false) end
    recording = false
    out(string.format("CLIPEND %s %d", clip, recorded))
end

local home, open, wall = nil, 0, 0
local function clear_length(m, yaw)
    local hit = collision_find_surface_on_ray(m.pos.x, m.pos.y + 70, m.pos.z, sins(yaw) * 4000, 0, coss(yaw) * 4000, 3)
    if hit.surface then return math.sqrt((hit.hitPos.x - m.pos.x) ^ 2 + (hit.hitPos.z - m.pos.z) ^ 2) end
    return 4000
end

local function clear_wanderers(m)
    for _, list in ipairs({OBJ_LIST_PUSHABLE, OBJ_LIST_DESTRUCTIVE, OBJ_LIST_GENACTOR}) do
        local o = obj_get_first(list)
        while o do
            local nxt = obj_get_next(o)
            if dist_between_objects(o, m.marioObj) < 4000 then obj_mark_for_deletion(o) end
            o = nxt
        end
    end

    for _, bhv in ipairs({id_bhvButterfly, id_bhvBird, id_bhvMessagePanel}) do
        local o = obj_get_first_with_behavior_id(bhv)
        while o do
            local nxt = obj_get_next_with_same_behavior_id(o)
            obj_mark_for_deletion(o)
            o = nxt
        end
    end
end
local function stage(m, yaw)
    clear_wanderers(m)
    m.pos.x, m.pos.y, m.pos.z = home.x, home.y, home.z
    m.vel.x, m.vel.y, m.vel.z, m.forwardVel = 0, 0, 0, 0
    set_mario_action(m, ACT_IDLE, 0)
    m.faceAngle.y = yaw
    reset_camera(m.area.camera)
end
local function cam_dist(m)
    local l = gLakituState
    return math.sqrt((l.pos.x - m.pos.x) ^ 2 + (l.pos.y - m.pos.y) ^ 2 + (l.pos.z - m.pos.z) ^ 2)
end

local function toward_open(m, mag)
    local a = open - m.area.camera.yaw
    input.x, input.y = math.floor(mag * sins(a)), math.floor(-mag * coss(a))
end

local function add_stage(side, line)
    add(function(m) stage(m, side and (line and line() or open) - 0x4000 or open) end, 3)
    if side then
        add(function(m) end, 30)
        add(function(m) m.faceAngle.y = line and line() or open end, 10)
    else
        add(function(m) input.pressed = R_TRIG end, 30)
    end
end

add(function() warp_to_level(LEVEL_CASTLE_GROUNDS, 1, 1) end, 90)
for _ = 1, 8 do add(function() if get_dialog_id() >= 0 then input.pressed = A_BUTTON end end, 15) end
add(function(m)
    local n = _G.charSelect.character_get_number_from_string("Kid Goku")
    _G.charSelect.character_set_current_number(n, 1)
    _G.charSelect.set_menu_open(false)
    hud_hide()
    home = {x = m.pos.x, y = m.pos.y, z = m.pos.z}

    local best = -1e9
    for k = 0, 31 do
        local yaw = k * 0x800
        local score = math.min(clear_length(m, yaw), 2500)
        for d = 250, 2000, 250 do
            local fy = find_floor_height(m.pos.x + sins(yaw) * d, m.pos.y + 400, m.pos.z + coss(yaw) * d)
            score = score - math.abs(fy - m.pos.y) * 3
        end
        if score > best then best, open = score, yaw end
    end
    out(string.format("INFO open line score %.0f", best))

    local nearest = 2200
    for k = 0, 31 do
        local yaw = k * 0x800
        local length = clear_length(m, yaw)
        if length > 500 and length < nearest then nearest, wall = length, yaw end
    end
    out(string.format("INFO wall %.0f away", nearest))
end, 5)
add_stage(false)
add(function(m) out(string.format("INFO staged camera %.0f units away", cam_dist(m))) end, 2)

add_stage(false)
add(function(m) start("stance") end, 75)
add(function(m) stop() end, 2)

add_stage(false)
add(function(m) start("run"); toward_open(m, 30) end, 45)
add(function(m) toward_open(m, 64) end, 60)
add(function(m) input.x, input.y = 0, 0 end, 20)
add(function(m) stop() end, 2)

add_stage(false)
add(function(m) start("jumps"); toward_open(m, 64) end, 25)
add(function(m) input.pressed = A_BUTTON; input.buttons = A_BUTTON end, 12)
add(function(m) input.buttons = 0 end, 14)
add(function(m) input.pressed = A_BUTTON; input.buttons = A_BUTTON end, 3)
add(function(m) input.buttons = A_BUTTON end, 22)
add(function(m) input.buttons = 0 end, 10)
add(function(m) input.pressed = A_BUTTON; input.buttons = A_BUTTON end, 3)
add(function(m) input.buttons = A_BUTTON end, 40)
add(function(m) input.buttons = 0; input.x, input.y = 0, 0 end, 30)
add(function(m) stop() end, 2)

add_stage(true)
add(function(m) start("jan-ken") end, 12)
add(function(m) input.pressed = B_BUTTON end, 9)
add(function(m) input.pressed = B_BUTTON end, 9)
add(function(m) input.pressed = B_BUTTON end, 34)
add(function(m) stop() end, 2)

add_stage(true)
add(function(m) start("kamehameha"); input.buttons = B_BUTTON; input.pressed = B_BUTTON end, 72)
add(function(m) input.buttons = 0 end, 62)
add(function(m) stop() end, 2)

add_stage(true, function() return wall end)
add(function(m) start("kamehameha-wall"); input.buttons = B_BUTTON; input.pressed = B_BUTTON end, 104)
add(function(m) input.buttons = 0 end, 70)
add(function(m) stop() end, 2)

add(function(m) stage(m, open) end, 40)
add(function(m) start("nimbus"); input.pressed = Y_BUTTON end, 34)
add(function(m) input.buttons = A_BUTTON end, 10)
add(function(m) input.buttons = 0; toward_open(m, 64) end, 70)
add(function(m) toward_open(m, 50) end, 40)
add(function(m) input.x, input.y = 0, 0; input.pressed = Y_BUTTON end, 45)
add(function(m) stop() end, 2)

add_stage(false)
add(function(m) start("side-kick"); toward_open(m, 20) end, 8)
add(function(m) input.pressed = B_BUTTON end, 40)
add(function(m) input.x, input.y = 0, 0 end, 10)
add(function(m) stop() end, 2)

add_stage(false)
add(function(m) start("lunge"); toward_open(m, 64) end, 30)
add(function(m) input.pressed = B_BUTTON end, 40)
add(function(m) input.x, input.y = 0, 0 end, 10)
add(function(m) stop() end, 2)

add_stage(true)
add(function(m) start("flying-kick"); input.pressed = A_BUTTON; input.buttons = A_BUTTON end, 8)
add(function(m) input.buttons = 0; input.pressed = B_BUTTON end, 50)
add(function(m) stop() end, 2)

add_stage(true)
add(function(m) start("leg-sweep"); input.buttons = Z_TRIG end, 10)
add(function(m) input.pressed = B_BUTTON end, 40)
add(function(m) input.buttons = 0 end, 10)
add(function(m) stop() end, 2)

add_stage(true)
add(function(m) start("backflip"); input.buttons = Z_TRIG end, 10)
add(function(m) input.pressed = A_BUTTON; input.buttons = Z_TRIG | A_BUTTON end, 45)
add(function(m) input.buttons = 0 end, 10)
add(function(m) stop() end, 2)

add_stage(false)
add(function(m) start("dive-leap"); toward_open(m, 64) end, 30)
add(function(m) input.buttons = Z_TRIG end, 2)
add(function(m) input.pressed = A_BUTTON; input.buttons = Z_TRIG | A_BUTTON end, 45)
add(function(m) input.buttons = 0; input.x, input.y = 0, 0 end, 15)
add(function(m) stop() end, 2)

add_stage(false)
add(function(m) start("slide-kick"); toward_open(m, 64) end, 30)
add(function(m) input.buttons = Z_TRIG end, 2)
add(function(m) input.pressed = B_BUTTON; input.buttons = Z_TRIG end, 40)
add(function(m) input.buttons = 0; input.x, input.y = 0, 0 end, 10)
add(function(m) stop() end, 2)

add_stage(true)
add(function(m) start("stomp"); input.pressed = A_BUTTON; input.buttons = A_BUTTON end, 12)
add(function(m) input.buttons = 0; input.pressed = Z_TRIG end, 50)
add(function(m) stop() end, 2)

add(function() out("DONE showcase") end)

hook_event(HOOK_MARIO_UPDATE, function(m)
    if m.playerIndex ~= 0 then return end
    if recording then recorded = recorded + 1 end
    if step > #steps then return end
    if wait > 0 then wait = wait - 1; return end
    local s = steps[step]
    step = step + 1
    local ok, err = pcall(s.f, m)
    if not ok then out("FAIL step " .. (step - 1) .. " " .. tostring(err)) end
    wait = s.frames - 1
end)
