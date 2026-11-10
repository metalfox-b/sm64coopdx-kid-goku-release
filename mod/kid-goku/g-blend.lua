if not _G.charSelectExists then return end

local floor, sin, cos, sqrt, atan, acos, asin, min, max = math.floor, math.sin, math.cos, math.sqrt, math.atan, math.acos,
    math.asin, math.min, math.max

local TO_RADIANS, TO_S16 = math.pi / 0x8000, 0x8000 / math.pi
local TAG_Y, TAG_Z = 0x4000, -0x4000
local NEAR = 0.012
local TURN_CUT = 0x1800
local TURN_FRAMES = 5

local JOINTS = {1, 2, 3, 4, 6, 7, 8, 10, 11, 12, 14, 15, 16, 18, 19}

local FRAMES = {
    idle = 8, look_l = 8, look_r = 8, stand = 8, walk = 7, run = 7, tiptoe = 7, tiptoe_step = 7, skid = 4, jump = 5, double = 5, fall = 8,
    land_single = 4, land_general = 4,
    tuck = 3, land = 4, flip = 3, backflip = 3, sideflip = 3, triple = 3, rock_in = 2, rock_out = 4, scissors_in = 2,
    scissors_out = 4, paper = 2, kick = 3, dive = 3, superman = 4, belly = 3, crouch = 4, crouch_in = 4, crouch_out = 5,
    crawl = 5, gp_start = 3, gp = 3, gp_land = 2, longjump = 3, kb_back = 2, kb_front = 2, kb_air_back = 2, kb_air_front = 2,
    lying_back = 6, lying_front = 6, dying = 4, hang = 3, climb = 4, ledge_climb = 4, swim = 6, flutter = 6, tread = 8,
    star = 6, scratch = 8, sleep = 10, tired = 10, yawn = 8, sit_down = 8, lie_down = 8, sleep_back = 8, panting = 8, hips = 10,
    flex = 8, double_fall = 6, stomp = 3, burn = 3, turn = 3, sideflip_land = 3, nimbus_lie = 22, shiver = 8, shocked = 2, push = 5, slide = 4, slide_kick = 3, wave = 6, stuck_head = 3,
    stuck_legs = 3, swing = 4, throw = 3, pick_up = 4, hold = 6, hold_walk = 6, hold_run = 6, heavy = 6, heavy_walk = 6, wing = 6,
    lunge = 3, lunge_skid = 3, stomp_enemy = 2, side_kick_in = 2, side_kick_out = 4, side_kick2_in = 2, side_kick2_out = 4, fight_ready = 5,
    twirl_start = 3, twirl = 4, hold_jump = 5, hold_fall = 8, hold_land = 4, hold_slide = 4, hold_stand_up = 5,
    kame_charge = 6, kame_fire = 2, nimbus_call = 5, nimbus_board = 3, nimbus_stand = 12, nimbus_ride = 18, nimbus_fly = 10, menu = 8,
}
local DEFAULT_FRAMES = 6

local FRAMES_LEAVING = {goku_kick_32 = 10, goku_lunge_20 = 8}

local SETS_OWN_FRAME = {goku_kame_charge = true, goku_kame_fire = true}

local frames_of = setmetatable({}, {__index = function(t, name)
    local n = FRAMES[(name:gsub("^goku_", ""):gsub("_%d+$", ""))] or DEFAULT_FRAMES
    t[name] = n
    return n
end})

local graph, turns, shift = nil, {}, nil

local dirty = false

local function walk(first, visit)
    local node = first
    repeat
        visit(node)
        if node.children then walk(node.children, visit) end
        node = node.next
    until not node or node == first
end

local function find_nodes(shared)
    graph, turns, shift = shared, {}, nil
    walk(shared, function(node)
        if node.type == GRAPH_NODE_TYPE_ROTATION then
            local rotation = cast_graph_node(node).rotation
            if rotation.y == TAG_Y and rotation.z == TAG_Z then
                local joint = floor(rotation.x * 180 / 0x8000 + 0.5) - 1
                turns[joint] = turns[joint] or {}
                table.insert(turns[joint], rotation)
                rotation.x, rotation.y, rotation.z = 0, 0, 0
            end
        elseif node.type == GRAPH_NODE_TYPE_TRANSLATION and not shift then
            shift = cast_graph_node(node).translation
        end
    end)
end

local function zero_nodes()
    for _, list in pairs(turns) do
        for i = 1, #list do
            local r = list[i]
            r.x, r.y, r.z = 0, 0, 0
        end
    end
    if shift then shift.x, shift.y, shift.z = 0, 0, 0 end
end

local function channel(clip, c, frame)
    local values, index = clip[1], clip[2]
    local v = values[index[2 * c + 2] + min(frame, index[2 * c + 1] - 1) + 1]
    return v >= 0x8000 and v - 0x10000 or v
end

local function multiply(aw, ax, ay, az, bw, bx, by, bz)
    return aw * bw - ax * bx - ay * by - az * bz, aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx, aw * bz + ax * by - ay * bx + az * bw
end

local function joint_rotation(clip, joint, frame)
    local c = 3 + 3 * joint
    local hx, hy, hz = channel(clip, c, frame) * TO_RADIANS / 2, channel(clip, c + 1, frame) * TO_RADIANS / 2,
        channel(clip, c + 2, frame) * TO_RADIANS / 2
    local cx, sx, cy, sy, cz, sz = cos(hx), sin(hx), cos(hy), sin(hy), cos(hz), sin(hz)
    return cz * cy * cx + sz * sy * sx, cz * cy * sx - sz * sy * cx, cz * sy * cx + sz * cy * sx, sz * cy * cx - cz * sy * sx
end

local function remaining(s)
    local x = (s.age + 1) / (s.length + 1)
    return 1 - x * x * (3 - 2 * x)
end

local function drawn_root(clip, c, frame)
    if clip.walks and c ~= 1 then return 0 end
    return channel(clip, c, frame)
end

local function begin(s, clip, frame, length, turned)
    local left = s.length > 0 and remaining(s) or 0
    for i = 1, #JOINTS do
        local joint = JOINTS[i]
        local w, x, y, z = joint_rotation(s.clip, joint, s.frame)
        local d = s.joints[joint]
        if d and left > 0 then
            local half = d[4] * left / 2
            local sh = sin(half)
            w, x, y, z = multiply(w, x, y, z, cos(half), d[1] * sh, d[2] * sh, d[3] * sh)
        end
        if joint == 1 and turned ~= 0 then
            local half = turned * TO_RADIANS / 2
            local bw, bx, by, bz = joint_rotation(clip, 0, frame)
            local tw, tx, ty, tz = multiply(bw, -bx, -by, -bz, cos(half), 0, sin(half), 0)
            tw, tx, ty, tz = multiply(tw, tx, ty, tz, bw, bx, by, bz)
            w, x, y, z = multiply(tw, tx, ty, tz, w, x, y, z)
        end
        local nw, nx, ny, nz = joint_rotation(clip, joint, frame)
        w, x, y, z = multiply(nw, -nx, -ny, -nz, w, x, y, z)
        if w < 0 then w, x, y, z = -w, -x, -y, -z end
        local angle = 2 * acos(min(1, w))
        if angle > NEAR then
            local axis = sqrt(max(1 - w * w, 1e-9))
            s.joints[joint] = d or {}
            local j = s.joints[joint]
            j[1], j[2], j[3], j[4] = x / axis, y / axis, z / axis, angle
        else
            s.joints[joint] = false
        end
    end
    local rx, ry, rz = s.rx * left, s.ry * left, s.rz * left
    s.rx = drawn_root(s.clip, 0, s.frame) + rx - drawn_root(clip, 0, frame)
    s.ry = drawn_root(s.clip, 1, s.frame) + ry - drawn_root(clip, 1, frame)
    s.rz = drawn_root(s.clip, 2, s.frame) + rz - drawn_root(clip, 2, frame)
    s.age, s.length = 0, length
end

local function write_nodes(s)
    local left = remaining(s)
    for i = 1, #JOINTS do
        local joint = JOINTS[i]
        local list, d = turns[joint], s.joints[joint]
        if list then
            local ex, ey, ez = 0, 0, 0
            if d then
                local half = d[4] * left / 2
                local sh = sin(half)
                local w, x, y, z = cos(half), d[1] * sh, d[2] * sh, d[3] * sh
                ex = floor(asin(max(-1, min(1, 2 * (w * x - y * z)))) * TO_S16 + 0.5)
                ey = floor(atan(2 * (x * z + w * y), 1 - 2 * (x * x + y * y)) * TO_S16 + 0.5)
                ez = floor(atan(2 * (x * y + w * z), 1 - 2 * (x * x + z * z)) * TO_S16 + 0.5)
            end
            for n = 1, #list do
                local r = list[n]
                r.x, r.y, r.z = ex, ey, ez
            end
        end
    end
    if shift then
        shift.x, shift.y, shift.z = floor(s.rx * left + 0.5), floor(s.ry * left + 0.5), floor(s.rz * left + 0.5)
    end
end

local states = {}
for i = 0, MAX_PLAYERS - 1 do
    states[i] = {name = nil, clip = nil, frame = 0, tick = -2, yaw = 0, age = 0, length = 0, joints = {}, rx = 0, ry = 0, rz = 0}
end

local function step(s, o)
    local tick = get_global_timer()
    if tick == s.tick then return end
    local info = o.header.gfx.animInfo
    local name = smlua_anim_util_get_current_animation_name(o)
    local clip = name and GOKU_CLIPS[name]
    local frame = max(info.animFrame, 0)
    local yaw = o.header.gfx.angle.y
    if s.length > 0 then
        s.age = s.age + 1
        if s.age >= s.length then s.length = 0 end
    end
    if clip and s.clip and tick == s.tick + 1 then
        local cut = name ~= s.name
        if not cut and not SETS_OWN_FRAME[name] then
            local anim = info.curAnim
            local moved = frame - s.frame
            local wrapped = moved < 0 and s.frame >= anim.loopEnd - 8 and frame <= anim.loopStart + 8
            cut = moved > 12 or (moved < 0 and not wrapped)
        end
        local turned = (s.yaw - yaw + 0x8000) % 0x10000 - 0x8000
        if cut then
            begin(s, clip, frame, max(frames_of[name], FRAMES_LEAVING[s.name] or 0), turned)
        elseif turned >= TURN_CUT or turned <= -TURN_CUT then
            begin(s, clip, frame, TURN_FRAMES, turned)
        end
    elseif not clip then
        s.length = 0
    end
    s.name, s.clip, s.frame, s.tick, s.yaw = name, clip, frame, tick, yaw
end

hook_event(HOOK_ON_OBJECT_ANIM_UPDATE, function(o)
    local m = geo_get_mario_state()
    if not m or m.marioObj ~= o or obj_has_model_extended(o, E_MODEL_GOKU) == 0 then return end
    local shared = o.header.gfx.sharedChild
    if not graph or shared ~= graph then find_nodes(shared) end
    local s = states[m.playerIndex]
    step(s, o)
    if s.length > 0 then
        write_nodes(s)
        dirty = true
    elseif dirty then
        zero_nodes()
        dirty = false
    end
end)

hook_event(HOOK_MARIO_UPDATE, function(m)
    local o = m.marioObj
    if o.hookRender == 0 and obj_has_model_extended(o, E_MODEL_GOKU) ~= 0 then o.hookRender = 1 end
end)

function goku_blending(i)
    return states[i].length > 0
end
