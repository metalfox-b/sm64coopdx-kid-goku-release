-- name: Kid Goku review
-- description: Plays each of his motions on real inputs with a close camera that follows him, one clip per shot, to

local function out(s) print("[GOKUTEST] " .. s) end

local input = {buttons = 0, pressed = 0, x = 0, y = 0}
local steps, step, wait = {}, 1, 0
local recorded, clip = 0, nil
local recording = false
local cam = nil
local eye = nil
local straight = false
local function add(f, frames) steps[#steps + 1] = {f = f, frames = frames or 1} end

hook_event(HOOK_BEFORE_MARIO_UPDATE, function(m)
    if m.playerIndex ~= 0 then return end
    if input.toward then
        local a = input.toward - m.area.camera.yaw
        input.x, input.y = math.floor(44 * sins(a)), math.floor(-44 * coss(a))
    end
    local c = m.controller
    c.buttonDown = input.buttons | input.pressed
    c.buttonPressed = input.pressed
    c.stickX, c.stickY = input.x, input.y
    c.stickMag = math.sqrt(input.x * input.x + input.y * input.y)
    local function raw(v) return v == 0 and 0 or v + (v > 0 and 6 or -6) end
    c.rawStickX, c.rawStickY = raw(input.x), raw(input.y)
    input.pressed = 0
end)

hook_event(HOOK_UPDATE, function()
    if not cam then return end
    local m = gMarioStates[0]
    local l = gLakituState
    if cam.spin then cam.yaw = cam.yaw + cam.spin end

    local ax, az = m.pos.x + sins(m.faceAngle.y) * (cam.ahead or 0), m.pos.z + coss(m.faceAngle.y) * (cam.ahead or 0)
    local ex, ey, ez = ax + sins(cam.yaw) * cam.dist, m.pos.y + cam.height, az + coss(cam.yaw) * cam.dist
    for _, v in ipairs({l.pos, l.curPos, l.goalPos}) do v.x, v.y, v.z = ex, ey, ez end
    for _, v in ipairs({l.focus, l.curFocus, l.goalFocus}) do v.x, v.y, v.z = ax, m.pos.y + cam.look, az end
end)

local function start(name)
    clip = name
    film_record(true)
    recording = true
    out(string.format("CLIP %s %d", name, recorded))
    out(string.format("ROLL %d %d", get_global_timer(), recorded))
end
local function stop()
    film_record(false)
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
    m.health = 0x880
    set_mario_action(m, ACT_IDLE, 0)
    set_mario_action(m, ACT_IDLE, 0)
    m.faceAngle.y = yaw
    m.intendedYaw = yaw
end

local function run_stick(m, mag)
    local a = open - m.area.camera.yaw
    input.x, input.y = math.floor(mag * sins(a)), math.floor(-mag * coss(a))
end

local function back_stick(m, mag)
    local a = open + 0x8000 - m.area.camera.yaw
    input.x, input.y = math.floor(mag * sins(a)), math.floor(-mag * coss(a))
end

local SIDE, QUARTER, FRONT, BACK = 0x4000, 0x2400, 0, 0x8000

local function rise_behind(m, cam_yaw)
    local away, most = cam_yaw + 0x8000, 0
    for d = 500, 3000, 250 do
        local fy = find_floor_height(m.pos.x + sins(away) * d, m.pos.y + 3000, m.pos.z + coss(away) * d)
        if fy > -10000 then most = math.max(most, fy - m.pos.y) end
    end
    return most
end

local function shot(name, angle, dist, height, look, beats, line, prep)
    if GOKU_SHOTS ~= "" and not ("," .. GOKU_SHOTS .. ","):find("," .. name .. ",", 1, true) then return end
    add(function(m)
        local yaw = line and line() or open
        stage(m, yaw)
        input.buttons, input.pressed, input.x, input.y = 0, 0, 0, 0

        local side = angle
        if angle ~= 0 and angle ~= BACK and rise_behind(m, yaw - angle) < rise_behind(m, yaw + angle) then side = -angle end
        cam = {yaw = yaw + side, dist = dist, height = height, look = look}
    end, 16)
    for _, b in ipairs(prep or {}) do add(b[2], b[1]) end
    add(function(m) start(name) end, 1)
    for _, b in ipairs(beats) do add(b[2], b[1]) end
    add(function(m) stop() end, 1)
end
local function press(b) input.pressed = b; input.buttons = b end
local function none() end

add(function() warp_to_level(LEVEL_CASTLE_GROUNDS, 1, 1) end, 90)
for _ = 1, 8 do add(function() if get_dialog_id() >= 0 then input.pressed = A_BUTTON end end, 15) end
add(function(m)
    local n = _G.charSelect.character_get_number_from_string("Kid Goku")
    _G.charSelect.character_set_current_number(n, 1)
    _G.charSelect.set_menu_open(false)
    camera_freeze()
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
end, 10)

shot("turntable", FRONT, 300, 90, 80, {{96, function() cam.spin = 0x2AB end}, {1, function() cam.spin = nil end}})
shot("idle", QUARTER, 260, 80, 78, {{90, none}})

for _, v in ipairs({{"low", 40}, {"level", 105}, {"high", 200}, {"top", 280}}) do
    shot("hair-" .. v[1], FRONT, 170, v[2], 112, {{96, function() cam.spin = 0x2AB end}, {1, function() cam.spin = nil end}})
end

shot("face-idle", 0x0600, 150, 82, 84, {{300, none}})

local function every_face()
    local beats = {}
    for e = 1, 17 do beats[e] = {20, function() eye, straight = e, true end} end
    beats[18] = {1, function() eye, straight = nil, false end}
    return beats
end
shot("faces-front", FRONT, 170, 76, 78, every_face())
shot("faces-quarter", QUARTER, 170, 76, 78, every_face())
shot("faces-side", SIDE, 170, 76, 78, every_face())

shot("faces-close", FRONT, 150, 70, 75, every_face())
shot("face-rest", 0x0600, 150, 82, 84, {{5, function() eye = 1 end}, {1, function() eye = nil end}})
shot("face-half", 0x0600, 150, 82, 84, {{5, function() eye = 9 end}})
shot("face-shut", 0x0600, 150, 82, 84, {{5, function() eye = 10 end}, {1, function() eye = nil end}})

shot("collar-run", 0x0600, 120, 62, 58, {{40, function(m) run_stick(m, 64) end}})
shot("neck-low", 0x0600, 130, 10, 62, {{6, none}})
shot("neck-low-side", QUARTER, 130, 10, 62, {{6, none}})
shot("neck-low-back", 0x7000, 130, 10, 62, {{6, none}})
shot("neck-low-run", 0x0600, 150, 10, 56, {{40, function(m) run_stick(m, 64) end}})
shot("collar-quarter", QUARTER, 130, 80, 58, {{40, function(m) run_stick(m, 64) end}})
shot("face-walk", 0x0600, 190, 70, 72, {{40, function(m) run_stick(m, 36) end}})
shot("face-run", 0x0600, 220, 70, 62, {{40, function(m) run_stick(m, 64) end}})
shot("face-stop", 0x0600, 220, 70, 66, {{30, function(m) run_stick(m, 64) end}, {50, function() input.x, input.y = 0, 0 end}})
shot("face-jump", 0x0600, 300, 90, 110, {{14, function() press(A_BUTTON) end}, {24, function() input.buttons = 0 end}})
shot("belt", 0x0600, 110, 46, 38, {{6, none}})
shot("belt-side", SIDE, 110, 46, 38, {{6, none}})
shot("belt-back", 0x7800, 110, 46, 38, {{6, none}})
shot("belt-run", QUARTER, 150, 50, 36, {{40, function(m) run_stick(m, 64) end}})

shot("flow", SIDE, 340, 90, 66, {
    {20, none}, {26, function(m) run_stick(m, 30) end}, {30, function(m) run_stick(m, 64) end},
    {22, function() input.x, input.y = 0, 0 end}, {10, none}, {26, function() press(A_BUTTON) end},
    {24, function() input.buttons = 0 end}, {12, function() input.pressed = B_BUTTON end}, {20, none},
})

local TURN = 0x2AB
local function tour(name, spin, frames, beats, height)
    local list = {{1, function() cam.spin = spin end}}
    for _, b in ipairs(beats or {}) do list[#list + 1] = b end
    list[#list + 1] = {frames, none}
    list[#list + 1] = {1, function() cam.spin = nil end}
    shot("lines-" .. name, FRONT, 190, height or 110, 48, list)
end
local function b_press() input.pressed = B_BUTTON end
local function a_tap() press(A_BUTTON) end
local function a_off() input.buttons = 0 end
tour("stand", TURN, 96)
tour("low", TURN, 96, nil, 20)
tour("tiptoe", TURN, 96, {{1, function(m) run_stick(m, 22) end}})
tour("walk", TURN, 96, {{1, function(m) run_stick(m, 44) end}})
tour("run", TURN * 2, 48, {{1, function(m) run_stick(m, 64) end}})
tour("jump", TURN, 72, {{1, a_tap}, {36, a_off}, {1, a_tap}, {36, a_off}})
tour("combo", TURN, 40, {{14, b_press}, {14, b_press}, {24, b_press}})
tour("kame", TURN, 96, {{96, function() press(B_BUTTON) end}, {1, a_off}})

shot("pants", FRONT, 170, 44, 34, {{96, function() cam.spin = 0x2AB end}, {1, function() cam.spin = nil end}})
shot("pants-low", FRONT, 170, 8, 34, {{96, function() cam.spin = 0x2AB end}, {1, function() cam.spin = nil end}})
shot("feet", SIDE, 90, 30, 12, {{6, none}})
shot("feet-back", 0x6000, 90, 30, 12, {{6, none}})
shot("feet-front", 0x0800, 110, 34, 12, {{6, none}})
shot("feet-quarter", QUARTER, 110, 44, 12, {{6, none}})
shot("feet-other", -SIDE, 90, 30, 12, {{6, none}})
shot("feet-run", SIDE, 150, 40, 22, {{40, function(m) run_stick(m, 64) end}})
shot("feet-walk", SIDE, 150, 40, 18, {{50, function(m) run_stick(m, 44) end}})
shot("arms", QUARTER, 170, 64, 56, {{6, none}})
shot("arms-other", -QUARTER, 170, 64, 56, {{6, none}})

shot("tiptoe", SIDE, 320, 90, 70, {{50, function(m) run_stick(m, 22) end}, {1, none}})
shot("walk", SIDE, 320, 90, 70, {{50, function(m) run_stick(m, 44) end}, {1, none}})
shot("run", SIDE, 340, 90, 70, {{70, function(m) run_stick(m, 64) end}, {26, function() input.x, input.y = 0, 0 end}})
shot("run-front", QUARTER, 360, 80, 70, {{64, function(m) run_stick(m, 64) end}})
shot("run-toward", 0x0600, 300, 62, 62, {{64, function(m) run_stick(m, 64) end}})
shot("run-behind", 0x7000, 300, 90, 62, {{64, function(m) run_stick(m, 64) end}})

shot("jumps", SIDE, 460, 120, 120, {
    {20, function(m) run_stick(m, 64) end}, {14, function() press(A_BUTTON) end}, {12, function() input.buttons = 0 end},
    {22, function() press(A_BUTTON) end}, {10, function() input.buttons = 0 end},
    {45, function() press(A_BUTTON) end}, {28, function() input.buttons = 0; input.x, input.y = 0, 0 end},
})
shot("backflip", SIDE, 440, 130, 130, {
    {12, function() input.buttons = Z_TRIG end}, {50, function() input.pressed = A_BUTTON; input.buttons = Z_TRIG | A_BUTTON end},
    {4, function() input.buttons = 0 end},
})
shot("long-jump", SIDE, 460, 110, 90, {
    {24, function(m) run_stick(m, 64) end}, {4, function() input.pressed = Z_TRIG; input.buttons = Z_TRIG end},
    {42, function() input.pressed = A_BUTTON; input.buttons = Z_TRIG | A_BUTTON end}, {8, function() input.buttons = 0; input.x, input.y = 0, 0 end},
})

shot("long-jump-high", SIDE, 520, 240, 60, {
    {24, function(m) run_stick(m, 64) end}, {4, function() input.pressed = Z_TRIG; input.buttons = Z_TRIG end},
    {42, function() input.pressed = A_BUTTON; input.buttons = Z_TRIG | A_BUTTON end}, {8, function() input.buttons = 0; input.x, input.y = 0, 0 end},
})
shot("long-jump-other", -SIDE, 460, 110, 90, {
    {24, function(m) run_stick(m, 64) end}, {4, function() input.pressed = Z_TRIG; input.buttons = Z_TRIG end},
    {42, function() input.pressed = A_BUTTON; input.buttons = Z_TRIG | A_BUTTON end}, {8, function() input.buttons = 0; input.x, input.y = 0, 0 end},
})
shot("long-jump-front", 0x0600, 300, 80, 70, {
    {24, function(m) run_stick(m, 64) end}, {4, function() input.pressed = Z_TRIG; input.buttons = Z_TRIG end},
    {42, function() input.pressed = A_BUTTON; input.buttons = Z_TRIG | A_BUTTON end}, {8, function() input.buttons = 0; input.x, input.y = 0, 0 end},
})

shot("jan-ken", SIDE, 260, 80, 72, {
    {9, function() input.pressed = B_BUTTON end}, {9, function() input.pressed = B_BUTTON end},
    {30, function() input.pressed = B_BUTTON end},
})
shot("jan-ken-front", QUARTER, 260, 80, 72, {
    {9, function() input.pressed = B_BUTTON end}, {9, function() input.pressed = B_BUTTON end},
    {30, function() input.pressed = B_BUTTON end},
})

local function kame(hold)
    return {{hold, function() press(B_BUTTON) end}, {52, function() input.buttons = 0 end}}
end
shot("kame-side", SIDE, 360, 90, 70, kame(90))
shot("kame-short", SIDE, 360, 90, 70, kame(30))
shot("kame-quarter", QUARTER, 360, 90, 70, kame(60))
shot("kame-back", 0x7000, 420, 130, 60, kame(45))
shot("kame-front", 0x0800, 300, 80, 55, kame(60))
shot("kame-other", -0x4000, 300, 80, 55, kame(60))

shot("kame-wall", SIDE, 620, 130, 70, {
    {100, function() press(B_BUTTON) end}, {64, function() input.buttons = 0 end},
}, function() return wall end, {{2, function() cam.ahead = 240 end}})
shot("kame-air", SIDE, 420, 120, 110, {
    {10, function() press(A_BUTTON) end}, {50, function() input.pressed = B_BUTTON; input.buttons = B_BUTTON end},
    {50, function() input.buttons = 0 end},
})

shot("air-kick", SIDE, 460, 120, 100, {
    {10, function() press(A_BUTTON) end}, {40, function() input.buttons = 0; input.pressed = B_BUTTON end},
})

local SWEEP = {{12, function() input.buttons = Z_TRIG end}, {40, function() input.pressed = B_BUTTON; input.buttons = Z_TRIG end}, {10, function() input.buttons = 0 end}}
shot("leg-sweep", SIDE, 260, 110, 30, SWEEP)
shot("leg-sweep-q", QUARTER, 240, 170, 20, SWEEP)

shot("slide-kick", SIDE, 420, 100, 40, {
    {24, function(m) run_stick(m, 64) end}, {2, function() input.pressed = Z_TRIG; input.buttons = Z_TRIG end},
    {40, function() input.pressed = B_BUTTON; input.buttons = Z_TRIG end}, {34, function() input.buttons = 0; input.x, input.y = 0, 0 end},
})

shot("ground-pound", SIDE, 420, 140, 110, {
    {12, function() press(A_BUTTON) end}, {50, function() input.buttons = 0; input.pressed = Z_TRIG end},
})

shot("b-kick", SIDE, 320, 100, 90, {{8, function() press(A_BUTTON) end}, {50, function() input.buttons = 0; input.pressed = B_BUTTON end}})
shot("b-kick-q", QUARTER, 320, 100, 90, {{8, function() press(A_BUTTON) end}, {50, function() input.buttons = 0; input.pressed = B_BUTTON end}})
shot("b-lunge", 0x3400, 340, 90, 60, {{34, function(m) run_stick(m, 64) end}, {60, function(m) input.pressed = B_BUTTON end}, {20, function() input.x, input.y = 0, 0 end}})
shot("b-walk-kick", 0x2800, 280, 80, 60, {{24, function(m) run_stick(m, 24) end}, {30, function(m) input.pressed = B_BUTTON end}, {10, function() input.x, input.y = 0, 0 end}})

shot("b-walk-kick-front", 0xD800, 280, 80, 60, {{24, function(m) run_stick(m, 24) end}, {30, function(m) input.pressed = B_BUTTON end}, {10, function() input.x, input.y = 0, 0 end}})

local goomba = nil
local function goomba_ahead(ahead)
    return function(m)
        local yaw = m.faceAngle.y
        local x, z = m.pos.x + sins(yaw) * ahead, m.pos.z + coss(yaw) * ahead
        goomba = {o = spawn_non_sync_object(id_bhvGoomba, E_MODEL_GOOMBA, x, m.pos.y, z, nil), x = x, z = z}

        local buddy = obj_get_first_with_behavior_id(id_bhvBobombBuddy)
        while buddy do
            obj_mark_for_deletion(buddy)
            buddy = obj_get_next_with_same_behavior_id(buddy)
        end
    end
end
hook_event(HOOK_UPDATE, function()
    if goomba and goomba.o.activeFlags ~= ACTIVE_FLAG_DEACTIVATED then goomba.o.oPosX, goomba.o.oPosZ, goomba.o.oForwardVel = goomba.x, goomba.z, 0 end
end)
hook_event(HOOK_ON_ATTACK_OBJECT, function(m, o, interaction)
    if goomba and o == goomba.o then
        out(string.format("INFO stomp 0x%x, %.0f off its middle", interaction, math.sqrt((m.pos.x - goomba.x) ^ 2 + (m.pos.z - goomba.z) ^ 2)))
    end
end)
shot("b-stomp", -0x4000, 460, 130, 30, {{1, function(m) press(A_BUTTON); run_stick(m, 34) end}, {1, function(m) m.forwardVel = 13 end}, {18, none},
    {50, function() input.buttons = 0; input.x, input.y = 0, 0 end}}, nil, {{4, goomba_ahead(296)}})
local function full_jump(angle) return {{8, none}, {18, function() press(A_BUTTON) end}, {30, function() input.buttons = 0 end}} end
shot("b-jump", 0x3000, 340, 100, 60, full_jump())
shot("b-jump-side", SIDE, 340, 100, 60, full_jump())
shot("b-ready", 0x1800, 280, 80, 60, {{4, function() input.pressed = B_BUTTON end}, {110, none}})
shot("b-combo", 0x1800, 280, 80, 60, {{14, function() input.pressed = B_BUTTON end}, {14, function() input.pressed = B_BUTTON end},
    {24, function() input.pressed = B_BUTTON end}, {50, none}})

shot("match-ready", 0x1800, 165, 112, 44, {{4, function() input.pressed = B_BUTTON end}, {110, none}})
shot("vault", SIDE, 640, 200, 180, {
    {10, function() press(A_BUTTON) end}, {70, function() input.buttons = 0; input.pressed = X_BUTTON end},
})

shot("tail-idle", 0x6000, 240, 80, 56, {{120, none}})
shot("tail-side", SIDE, 240, 70, 56, {{120, none}})
shot("tail-back", BACK, 240, 80, 56, {{120, none}})
shot("tail-run", 0x5000, 300, 90, 60, {{60, function(m) run_stick(m, 64) end}, {30, function() input.x, input.y = 0, 0 end}})
shot("tail-turn", 0x5000, 300, 90, 60, {
    {30, function(m) run_stick(m, 64) end}, {26, function(m) back_stick(m, 64) end}, {30, function() input.x, input.y = 0, 0 end},
})
shot("tail-jump", SIDE, 460, 170, 150, {{4, function() press(A_BUTTON) end}, {56, function() input.buttons = 0 end}})

shot("nimbus", QUARTER, 520, 140, 100, {
    {36, function() input.pressed = Y_BUTTON end}, {20, function() input.buttons = A_BUTTON end},
    {50, function(m) input.buttons = 0; run_stick(m, 64) end},
    {30, function() input.x, input.y = 0, 0; input.pressed = Y_BUTTON end},
})

local function call_nimbus(frames) return {frames, function() input.pressed = Y_BUTTON end} end
local function up_high(frames) return {frames, function() input.buttons = A_BUTTON end} end
local function let_go(frames, f) return {frames, function(m) input.buttons = 0; if f then f(m) end end} end
local function steer(frames, turn)
    return {frames, function(m)
        local a = open + turn - m.area.camera.yaw
        input.x, input.y = math.floor(64 * sins(a)), math.floor(-64 * coss(a))
    end}
end

local ON = {call_nimbus(50)}
local ON_HIGH = {call_nimbus(50), up_high(30), let_go(1)}
shot("n-board", 0xE000, 520, 120, 100, {call_nimbus(90)})
shot("n-off", 0xE000, 520, 120, 80, {
    call_nimbus(66), {40, function() input.buttons = A_BUTTON end}, {50, function() input.buttons = 0; input.pressed = Y_BUTTON end},
})
shot("n-stand", 0x0800, 300, 70, 50, {{90, none}}, nil, ON)
shot("n-stand-q", QUARTER, 300, 70, 50, {{90, none}}, nil, ON)
shot("n-fly", 0x2C00, 300, 70, 50, {let_go(90, function(m) run_stick(m, 64) end)}, nil, ON_HIGH)
shot("n-fly-front", 0x0C00, 300, 70, 50, {let_go(90, function(m) run_stick(m, 64) end)}, nil, ON_HIGH)
shot("n-fly-back", 0x7000, 300, 70, 50, {let_go(90, function(m) run_stick(m, 64) end)}, nil, ON_HIGH)
shot("n-turn", 0x3000, 340, 90, 50, {
    let_go(40, function(m) run_stick(m, 64) end), {40, function(m) back_stick(m, 64) end},
    {30, function() input.x, input.y = 0, 0 end},
}, nil, ON_HIGH)
shot("n-bank", BACK, 340, 110, 60, {let_go(40, function(m) run_stick(m, 64) end), steer(30, 0x5000), steer(30, -0x2000)}, nil, ON_HIGH)
shot("n-climb", 0x3000, 340, 90, 50, {up_high(30), {30, function() input.buttons = Z_TRIG end}, {12, function() input.buttons = 0 end}}, nil, ON)
shot("n-sit", 0x1800, 260, 70, 34, {{60, none}, {110, none}}, nil, ON)
shot("n-sit-front", 0x0400, 260, 70, 34, {{60, none}, {110, none}}, nil, ON)
shot("n-lie", 0x2400, 260, 70, 34, {{350, none}, {50, none}}, nil, ON)

shot("hurt", SIDE, 340, 90, 70, {
    {50, function(m) m.forwardVel = -24; m.invincTimer = 30; set_mario_action(m, ACT_BACKWARD_GROUND_KB, 0) end},
})

local function forced(name, action, frames, stick)
    shot(name, QUARTER, 300, 80, 60, {{frames, function(m)
        set_mario_action(m, action, 0)
        if stick then run_stick(m, stick) end
    end}})
end
forced("crouch", ACT_CROUCHING, 24)
forced("crawl", ACT_CRAWLING, 40, 40)
forced("sleep", ACT_START_SLEEPING, 110)
forced("sleeping", ACT_SLEEPING, 30)
forced("forced-slide-kick", ACT_SLIDE_KICK, 30)
forced("forced-ground-pound", ACT_GROUND_POUND_LAND, 20)
forced("tiptoe-still", ACT_PANTING, 30)
forced("dive", ACT_DIVE, 24)
forced("hang", ACT_LEDGE_GRAB, 24)
forced("hold", ACT_HOLD_IDLE, 24)
forced("swim", ACT_WATER_IDLE, 24)

local function who(name)
    return function()
        local n = _G.charSelect.character_get_number_from_string(name)
        _G.charSelect.character_set_current_number(n, 1)
    end
end
local tree, king = nil, nil
for _, c in ipairs({{"", "Kid Goku"}, {"-mario", "Mario"}}) do
    local swap, back = {{6, who(c[2])}}, {1, who("Kid Goku")}

    shot("r-tree" .. c[1], QUARTER, 380, 130, 100, {
        {1, function(m)
            local yaw = m.faceAngle.y
            tree = spawn_non_sync_object(id_bhvTree, E_MODEL_BUBBLY_TREE, m.pos.x + sins(yaw) * 330, m.pos.y, m.pos.z + coss(yaw) * 330, nil)
        end},
        {14, function(m) run_stick(m, 64) end},
        {1, function() press(A_BUTTON) end},
        {30, function(m) run_stick(m, 64) end},
        {40, function() input.x, input.y = 0, 0 end},
        {30, function(m) input.x, input.y = 0, 64 end},
        {50, function() input.x, input.y = 0, 0 end},
        {1, function(m) if tree then obj_mark_for_deletion(tree) end; set_mario_action(m, ACT_IDLE, 0) end},
        back,
    }, nil, swap)

    for _, view in ipairs({{"", 0x3000}, {"-back", BACK}, {"-side", 0x6000}}) do
    shot("r-grabbed" .. c[1] .. view[1], view[2], 560, 190, 120, {
        {1, function(m)
            local yaw = m.faceAngle.y
            king = spawn_non_sync_object(id_bhvKingBobomb, E_MODEL_KING_BOBOMB, m.pos.x + sins(yaw) * 420, m.pos.y, m.pos.z + coss(yaw) * 420, function(k)
                k.oMoveAngleYaw = yaw + 0x8000
                k.oAction = 2
            end)
        end},
        {260, function(m) if get_dialog_id() >= 0 then input.pressed = A_BUTTON end end},
        {1, function(m) if king then obj_mark_for_deletion(king) end; set_mario_action(m, ACT_IDLE, 0) end},
        back,
    }, nil, swap)
    end
end

local ACT_REVIEW_HOLD = allocate_mario_action(ACT_GROUP_STATIONARY | ACT_FLAG_STATIONARY)
hook_mario_action(ACT_REVIEW_HOLD, function(m) return 0 end)
local held = nil
hook_event(HOOK_ON_OBJECT_RENDER, function(o)
    local m = gMarioStates[0]
    if held and o == m.marioObj then smlua_anim_util_set_animation(o, held) end
end)
local function pose(name, clip, frames, angle, camEye, look, dist, height)
    shot(name, angle or QUARTER, dist or 300, height or 80, look or 62, {
        {frames, function(m)
            set_mario_action(m, ACT_REVIEW_HOLD, 0)
            set_character_animation(m, CHAR_ANIM_FIRST_PERSON)
            set_anim_to_frame(m, 0)
            held = clip
            eye = camEye
        end},
        {1, function(m) held, eye = nil, nil; set_mario_action(m, ACT_IDLE, 0) end},
    })
end
pose("p-hips", "goku_hips", 75, 0x0400, nil, 50, 240, 60)
pose("p-wolf", "goku_stomp_enemy", 24, SIDE, MARIO_EYES_LOOK_DOWN, 50, 260, 95)
pose("p-wolf-q", "goku_stomp_enemy", 24, 0x3000, MARIO_EYES_LOOK_DOWN, 50, 260, 95)
pose("p-kick", "goku_kick_32", 32, QUARTER, 7, 90, 300, 90)
pose("p-kick-s", "goku_kick_32", 32, SIDE, 7, 90, 300, 90)
pose("p-lunge", "goku_lunge_20", 20, QUARTER, 2, 90, 300, 90)
pose("p-side-kick", "goku_side_kick_out", 14, 0x2000, 1, 60, 260, 80)
pose("p-side-kick-s", "goku_side_kick_out", 14, SIDE, 1, 60, 260, 80)
pose("p-ready", "goku_fight_ready", 40, 0x0800, 4, 50, 240, 70)
pose("p-flex", "goku_flex", 60, 0x0800)
pose("p-tired", "goku_tired_50", 50, QUARTER, 2)
pose("p-yawn", "goku_yawn_59", 59, 0x0800, 3)
pose("p-sit", "goku_sit_down_64", 64, QUARTER, 2)
pose("p-lie", "goku_lie_down_40", 40, QUARTER, 10)
pose("p-sleep", "goku_sleep_back_50", 50, QUARTER, 10, 30, 300, 120)
pose("p-pant", "goku_panting_20", 20, 0x1800, 2)
pose("p-stomp", "goku_stomp_11", 11, SIDE)
pose("p-gp-land", "goku_gp_land_6", 6, SIDE)
pose("p-star", "goku_star_63", 63, 0x0800, 7)
pose("p-burn", "goku_burn_10", 10, QUARTER, 6)
pose("p-jump", "goku_jump_38", 38, SIDE, 7, 90, 340, 90)
pose("p-double", "goku_double_6", 6, QUARTER, 7, 90, 340, 90)
pose("p-fall", "goku_fall_24", 24, QUARTER, 6, 90, 340, 90)
pose("p-call", "goku_nimbus_call", 30, 0x1000, 5)
pose("p-lie-nimbus", "goku_nimbus_lie", 80, QUARTER, 7, 40, 300, 110)
pose("p-turn", "goku_turn_18", 18, SIDE)
pose("p-jump-q", "goku_jump_38", 38, QUARTER, 7, 90, 340, 90)
pose("p-double-s", "goku_double_6", 6, SIDE, 7, 90, 340, 90)

for _, t in ipairs({
    {"back-spin", "goku_back_spin_10", 24}, {"belly", "goku_belly_80", 40}, {"climb", "goku_climb_90", 90},
    {"flip", "goku_flip_42", 52}, {"flutter", "goku_flutter_24", 48}, {"hang", "goku_hang_90", 40},
    {"heavy", "goku_heavy_40", 40}, {"heavy-walk", "goku_heavy_walk_90", 90}, {"hold", "goku_hold_61", 40},
    {"hold-fall", "goku_hold_fall_15", 30}, {"hold-jump", "goku_hold_jump_10", 24}, {"hold-land", "goku_hold_land_19", 29},
    {"hold-run", "goku_hold_run_76", 76}, {"hold-slide", "goku_hold_slide_14", 24}, {"hold-stand-up", "goku_hold_stand_up_37", 47},
    {"hold-walk", "goku_hold_walk_90", 90}, {"kb-air-back", "goku_kb_air_back_80", 40}, {"kb-air-front", "goku_kb_air_front_80", 40},
    {"kb-front", "goku_kb_front_30", 40}, {"land-ready", "goku_land_ready", 26}, {"ledge-climb", "goku_ledge_climb_10", 24},
    {"lying-back", "goku_lying_back_70", 30}, {"lying-front", "goku_lying_front_47", 30}, {"pick-up", "goku_pick_up_37", 47},
    {"push", "goku_push_90", 90}, {"scratch", "goku_scratch_90", 90}, {"shiver", "goku_shiver_90", 90},
    {"shocked", "goku_shocked_53", 53}, {"sideflip-land", "goku_sideflip_land_10", 24, QUARTER + BACK}, {"slide", "goku_slide_20", 30},
    {"stuck-head", "goku_stuck_head_90", 90}, {"stuck-legs", "goku_stuck_legs_90", 90}, {"superman", "goku_superman_15", 30},
    {"swim", "goku_swim_16", 32}, {"swing", "goku_swing_50", 50}, {"throw", "goku_throw_40", 50},
    {"tread", "goku_tread_30", 60}, {"triple", "goku_triple_36", 46}, {"twirl", "goku_twirl_1", 24},
    {"twirl-start", "goku_twirl_start_5", 24}, {"wave", "goku_wave_90", 90}, {"wing", "goku_wing_40", 80},
}) do
    pose("t-" .. t[1], t[2], t[3], t[4] or QUARTER, nil, 62, 340, 90)
end

pose("p-superman-front", "goku_superman_15", 12, FRONT, nil, 70, 190, 90)
pose("p-superman-side", "goku_superman_15", 12, SIDE, nil, 70, 190, 90)
pose("p-superman-quarter", "goku_superman_15", 12, 0x1800, nil, 70, 170, 150)

shot("r-wing", 0x3000, 560, 140, 60, {
    {1, function(m)
        m.flags = m.flags | MARIO_WING_CAP
        m.capTimer = 900
        m.forwardVel = 40
        set_mario_action(m, ACT_FLYING_TRIPLE_JUMP, 0)
    end},
    {150, none}, {1, function(m) m.flags = m.flags & ~MARIO_WING_CAP; m.capTimer = 0 end}, {40, none},
    {1, function(m) set_mario_action(m, ACT_IDLE, 0) end},
})

local waiting = nil
shot("r-ball", 0x0400, 360, 80, 55, {
    {1, function(m)
        local yaw = m.faceAngle.y - 0x4000
        waiting = spawn_non_sync_object(id_bhvWingCap, E_MODEL_MARIOS_WING_CAP, m.pos.x + sins(yaw) * 130, m.pos.y + 30,
            m.pos.z + coss(yaw) * 130, nil)
    end},
    {50, none},
    {1, function(m)
        if waiting then obj_mark_for_deletion(waiting) end
        m.flags = m.flags | MARIO_WING_CAP
        m.capTimer = 600
    end},
    {40, none}, {50, function(m) run_stick(m, 40) end},
    {1, function(m) input.x, input.y = 0, 0; m.flags = m.flags & ~MARIO_WING_CAP; m.capTimer = 0 end}, {10, none},
})

shot("r-twirl", QUARTER, 420, 100, 70, {{70, none}, {1, function(m) set_mario_action(m, ACT_IDLE, 0) end}}, nil,
    {{3, function(m) m.pos.y = m.pos.y + 500; set_mario_action(m, ACT_TWIRLING, 0) end}})

shot("r-carry-jump", SIDE, 420, 110, 90, {{1, function(m) set_mario_action(m, ACT_HOLD_JUMP, 0) end}, {50, none},
    {1, function(m) set_mario_action(m, ACT_IDLE, 0) end}})

shot("r-fidget", 0x0C00, 260, 70, 56, {{136, function(m) m.actionTimer = 1 end}, {70, function(m) m.actionTimer = 3 end}})
shot("r-lying", QUARTER, 340, 130, 40, {
    {1, function(m) set_mario_action(m, ACT_SLEEPING, 0); m.actionState = 1 end}, {150, none},
    {60, function(m) run_stick(m, 40) end}, {1, function() input.x, input.y = 0, 0 end},
})
shot("r-nod", 0x0600, 300, 90, 40, {{1, function(m) set_mario_action(m, ACT_SLEEPING, 0) end}, {90, none},
    {50, function(m) run_stick(m, 40) end}, {1, function() input.x, input.y = 0, 0 end}})
shot("r-lie-close", 0x1800, 260, 70, 34, {
    {36, function() input.pressed = Y_BUTTON end}, {20, function() input.buttons = A_BUTTON end},
    {200, function() input.buttons = 0 end}, {60, none}, {26, function() input.pressed = Y_BUTTON end},
})
shot("r-wake", QUARTER, 300, 90, 40, {{1, function(m) set_mario_action(m, ACT_SLEEPING, 0) end}, {50, none},
    {1, function(m) run_stick(m, 40) end}, {45, function() input.x, input.y = 0, 0 end}})
shot("r-tiptoe", SIDE, 320, 90, 70, {{125, function(m) run_stick(m, 22) end}, {1, none}})
shot("r-tiptoe-side", SIDE, 210, 62, 42, {{125, function(m) run_stick(m, 22) end}, {1, none}})
shot("r-tiptoe-front", FRONT, 250, 62, 45, {{125, function(m) run_stick(m, 22) end}, {1, none}})
shot("r-sleep", QUARTER, 340, 120, 50, {{1, function(m) set_mario_action(m, ACT_START_SLEEPING, 0) end}, {430, none}})
shot("r-turn", SIDE, 420, 90, 66, {{44, function(m) run_stick(m, 64) end}, {50, function(m) back_stick(m, 64) end}})
shot("r-sideflip", SIDE, 460, 110, 90, {
    {44, function(m) run_stick(m, 64) end}, {5, function(m) back_stick(m, 64) end},
    {50, function() press(A_BUTTON) end}, {14, function() input.buttons, input.x, input.y = 0, 0, 0 end},
})
shot("r-gp", SIDE, 420, 120, 120, {
    {18, function() press(A_BUTTON) end}, {46, function() input.buttons = 0; input.pressed = Z_TRIG end},
})
shot("r-lie", QUARTER, 400, 130, 90, {
    {36, function() input.pressed = Y_BUTTON end}, {20, function() input.buttons = A_BUTTON end},
    {230, function() input.buttons = 0 end},
    {26, function() input.pressed = Y_BUTTON end},
})

if GOKU_SHOTS == "" or ("," .. GOKU_SHOTS .. ","):find(",door,", 1, true) then
    add(function() warp_to_level(LEVEL_CASTLE, 1, 0) end, 120)
    for _ = 1, 4 do add(function() if get_dialog_id() >= 0 then input.pressed = A_BUTTON end end, 15) end
    local going = 0
    local function through(sign)
        add(function(m)
            local o = obj_get_first_with_behavior_id(id_bhvDoor)
            while o and (o.oBehParams >> 24) & 0xFF ~= 0 do o = obj_get_next_with_same_behavior_id(o) end
            if not o then out("FAIL no door"); return end
            local yaw = o.oMoveAngleYaw
            input.buttons, input.pressed, input.x, input.y, input.toward = 0, 0, 0, 0, nil
            going = yaw + (sign > 0 and 0x8000 or 0)
            m.pos.x, m.pos.y, m.pos.z = o.oPosX + sins(yaw) * 170 * sign, o.oPosY, o.oPosZ + coss(yaw) * 170 * sign
            m.vel.x, m.vel.y, m.vel.z, m.forwardVel = 0, 0, 0, 0
            m.faceAngle.y = yaw + (sign > 0 and 0x8000 or 0)
            set_mario_action(m, ACT_IDLE, 0)
            cam = {yaw = yaw + (sign > 0 and 0 or 0x8000) + 0x1400, dist = 380, height = 110, look = 70}
        end, 8)
        add(function(m) input.toward = going end, 86)
        add(function() input.toward, input.x, input.y = nil, 0, 0 end, 30)
    end
    add(function(m) start("door") end, 1)
    through(1)
    through(-1)
    add(function(m) stop() end, 1)
end
add(function() out("DONE review") end)

hook_event(HOOK_MARIO_UPDATE, function(m)
    if m.playerIndex ~= 0 then return end
    if eye then m.marioBodyState.eyeState = eye end
    if straight and m.action == ACT_IDLE then m.actionState, m.actionTimer = 2, 0 end
    if recording then recorded = recorded + 1 end
    if step > #steps then return end
    if wait > 0 then wait = wait - 1; return end
    local s = steps[step]
    step = step + 1
    local ok, err = pcall(s.f, m)
    if not ok then out("FAIL step " .. (step - 1) .. " " .. tostring(err)) end
    wait = s.frames - 1
end)

local chargeHead = nil
hook_event(HOOK_MARIO_UPDATE, function(m)
    if m.playerIndex ~= 0 then return end
    if m.action ~= _G.kidGoku.actions.kame or m.actionState ~= 0 or m.actionTimer < 40 or m.pos.y > m.floorHeight + 4 then
        chargeHead = nil
        return
    end
    local h = m.marioBodyState.headPos
    if chargeHead and math.abs(h.x - chargeHead.x) + math.abs(h.y - chargeHead.y) + math.abs(h.z - chargeHead.z) > 0.05 then
        out("FAIL his head moves in the charge")
    end
    chargeHead = {x = h.x, y = h.y, z = h.z}
end)
