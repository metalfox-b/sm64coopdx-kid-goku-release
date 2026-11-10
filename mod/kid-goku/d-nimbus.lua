if not _G.charSelectExists then return end

ACT_GOKU_NIMBUS_CALL = allocate_mario_action(ACT_GROUP_STATIONARY | ACT_FLAG_STATIONARY)
ACT_GOKU_NIMBUS = allocate_mario_action(ACT_GROUP_AIRBORNE | ACT_FLAG_AIR)

local CALL_FRAMES = 30
local SPEED = 60
local CLIMB = 28
local OPEN_SKY = 1500
local SIT_DOWN = 110
local LIE_BACK = 320
local BOARD = 26
local CATCH = 10

local RIDE_DROP = 36
local ARRIVE = 26
local WAIT_BESIDE = 190
local WAIT_ABOVE = 12
local LANDING = 16
local TURN = 0x500

local function ease_out(s) return 1 - (1 - s) * (1 - s) * (1 - s) end
local function smooth(s) return s * s * (3 - 2 * s) end
local function wrap(a) return (a + 0x8000) % 0x10000 - 0x8000 end

local TRAIL_LINKS, TRAIL_EVERY, TRAIL_TAPER = 14, 2, 0.86
local TRAIL_WIDE, TRAIL_FLAT = 0.5, 0.7
local TRAIL_FROM = 95
local TRAIL_FULL = 30
local trails, trailCount = {}, 0

id_bhvGokuTrail = hook_behavior(nil, OBJ_LIST_DEFAULT, true, function(o)
    o.oFlags = 0
end, function(o)
    local cloud = o.parentObj
    if not goku_alive(cloud) or get_id_from_behavior(cloud.behavior) ~= id_bhvGokuNimbus or trails[cloud.oHealth] == nil then
        obj_mark_for_deletion(o)
    end
end, "bhvGokuTrail")

local function trail_update(o)
    local yaw = o.oFaceAngleYaw
    local x, y, z = o.oPosX - sins(yaw) * TRAIL_FROM, o.oPosY, o.oPosZ - coss(yaw) * TRAIL_FROM
    local t = trails[o.oHealth]
    if not t then
        t = {x = {}, y = {}, z = {}, links = {}, wide = 0}
        for k = 1, TRAIL_LINKS * TRAIL_EVERY + 1 do t.x[k], t.y[k], t.z[k] = x, y, z end
        for j = 1, TRAIL_LINKS do
            t.links[j] = spawn_non_sync_object(id_bhvGokuTrail, E_MODEL_GOKU_TRAIL, x, y, z, function(link)
                link.parentObj = o
                link.header.gfx.node.flags = link.header.gfx.node.flags | GRAPH_RENDER_INVISIBLE
            end)
        end
        trails[o.oHealth] = t
    end
    table.insert(t.x, 1, x); table.insert(t.y, 1, y); table.insert(t.z, 1, z)
    table.remove(t.x); table.remove(t.y); table.remove(t.z)
    local speed = math.sqrt((t.x[1] - t.x[2]) ^ 2 + (t.y[1] - t.y[2]) ^ 2 + (t.z[1] - t.z[2]) ^ 2)
    t.wide = t.wide + (TRAIL_WIDE * math.min(1, speed / TRAIL_FULL) - t.wide) * 0.2
    for j = 1, TRAIL_LINKS do
        local link = t.links[j]
        if goku_alive(link) then
            local a, b = (j - 1) * TRAIL_EVERY + 1, j * TRAIL_EVERY + 1
            local dx, dy, dz = t.x[b] - t.x[a], t.y[b] - t.y[a], t.z[b] - t.z[a]
            local long = math.sqrt(dx * dx + dy * dy + dz * dz)
            local gfx = link.header.gfx
            if long > 2 and t.wide > 0.02 then
                local wide = t.wide * TRAIL_TAPER ^ (j - 1)
                gfx.pos.x, gfx.pos.y, gfx.pos.z = t.x[a], t.y[a], t.z[a]
                gfx.angle.x, gfx.angle.y, gfx.angle.z = wrap(-atan2s(math.sqrt(dx * dx + dz * dz), dy)), wrap(atan2s(dz, dx)), 0
                gfx.scale.x, gfx.scale.y, gfx.scale.z = wide, wide * TRAIL_FLAT, long / 100
                gfx.node.flags = gfx.node.flags & ~GRAPH_RENDER_INVISIBLE
            else
                gfx.node.flags = gfx.node.flags | GRAPH_RENDER_INVISIBLE
            end
        end
    end
end

id_bhvGokuNimbus = hook_behavior(nil, OBJ_LIST_DEFAULT, true, function(o)
    o.oFlags = OBJ_FLAG_UPDATE_GFX_POS_AND_ANGLE
    o.oAction = 0
end, function(o)
    local m = gMarioStates[network_local_index_from_global(o.oGokuOwner)]
    if m and goku_gone(m) then m = nil end
    local riding = m and (m.action == ACT_GOKU_NIMBUS or m.action == ACT_FLYING)
    local calling = m and (m.action == ACT_GOKU_NIMBUS_CALL or m.action == ACT_FLYING_TRIPLE_JUMP)
    if o.oAction < 3 and not riding and not calling then
        o.oAction = 3
        o.oTimer = 0
    end
    if o.oAction == 0 then

        local s = math.min(o.oTimer / ARRIVE, 1)
        local e = ease_out(s)
        local to = o.oMoveAngleYaw
        local dx, dz = m.pos.x + sins(to) * WAIT_BESIDE, m.pos.z + coss(to) * WAIT_BESIDE
        local bend = sins(math.floor(e * 0x8000)) * 420
        o.oPosX = o.oHomeX + (dx - o.oHomeX) * e + coss(to) * bend
        o.oPosY = o.oHomeY + (m.pos.y + WAIT_ABOVE - o.oHomeY) * e
        o.oPosZ = o.oHomeZ + (dz - o.oHomeZ) * e - sins(to) * bend
        o.oFaceAngleRoll = math.floor(sins(math.floor(e * 0x8000)) * 0x1400)
        if riding then
            o.oHomeX, o.oHomeY, o.oHomeZ = o.oPosX, o.oPosY, o.oPosZ
            o.oAction = 1
        end
    elseif o.oAction == 1 then

        local t = m.action == ACT_FLYING and o.oTimer or m.actionTimer
        local e = smooth(math.min(t / CATCH, 1))
        o.oPosX = o.oHomeX + (m.pos.x - o.oHomeX) * e
        o.oPosY = o.oHomeY + (m.pos.y - RIDE_DROP - o.oHomeY) * e
        o.oPosZ = o.oHomeZ + (m.pos.z - o.oHomeZ) * e
        o.oFaceAngleYaw = o.oFaceAngleYaw + wrap(m.faceAngle.y - o.oFaceAngleYaw) * e
        o.oFaceAngleRoll = o.oFaceAngleRoll * 0.8
        if t >= CATCH then o.oAction = 2 end
    elseif o.oAction == 2 then

        local g, yaw = gGoku[m.playerIndex], m.faceAngle.y

        local squash = m.action == ACT_FLYING and math.max(0.12, math.min(1, (m.pos.y - m.floorHeight) / (RIDE_DROP * 2))) or 1
        local drop = RIDE_DROP * squash
        local back, over = sins(g.nimbusPitch) * drop, sins(g.nimbusRoll) * drop
        o.oPosX = m.pos.x - sins(yaw) * back + sins(yaw + 0x4000) * over
        o.oPosY = m.pos.y - drop + g.nimbusBob
        o.oPosZ = m.pos.z - coss(yaw) * back + coss(yaw + 0x4000) * over
        o.header.gfx.scale.y = squash
        o.oFaceAngleYaw, o.oFaceAnglePitch, o.oFaceAngleRoll = yaw, g.nimbusPitch, g.nimbusRoll
    else

        local speed = math.min(o.oTimer * 3, 45)
        o.header.gfx.scale.y = math.min(1, o.header.gfx.scale.y + 0.15)
        o.oPosY = o.oPosY + speed * 0.7
        o.oPosX = o.oPosX + sins(o.oFaceAngleYaw) * speed
        o.oPosZ = o.oPosZ + coss(o.oFaceAngleYaw) * speed
        o.oFaceAnglePitch = o.oFaceAnglePitch * 0.9
        o.oFaceAngleRoll = o.oFaceAngleRoll * 0.9
        if o.oTimer > 60 then
            trails[o.oHealth] = nil
            obj_mark_for_deletion(o)
            return
        end
    end
    trail_update(o)
end, "bhvGokuNimbus")

local function open_sky(m)
    return find_ceil_height(m.pos.x, m.pos.y + 80, m.pos.z) > m.pos.y + OPEN_SKY
end

local NIMBUS_COMES, NIMBUS_GOES = 0.7, 0.5
local ZIP_AT, ZIP_REST = 30, 75

local function send_cloud(m, turn, away, up)
    local yaw = m.faceAngle.y + turn
    local x, y, z = m.pos.x + sins(yaw) * away, m.pos.y + up, m.pos.z + coss(yaw) * away
    gGoku[m.playerIndex].nimbus = spawn_non_sync_object(id_bhvGokuNimbus, E_MODEL_GOKU_NIMBUS, x, y, z, function(o)
        o.oGokuOwner = network_global_index_from_local(m.playerIndex)
        trailCount = trailCount + 1
        o.oHealth = trailCount
        o.oFaceAngleYaw = yaw + 0x8000
        o.oMoveAngleYaw = yaw
        o.oHomeX, o.oHomeY, o.oHomeZ = x, y, z
    end)
    goku_sound(m, "goku_nimbus.ogg", NIMBUS_COMES, {x = x, y = y, z = z})
end

local function has_cloud(m)
    local o = gGoku[m.playerIndex].nimbus
    return goku_alive(o) and get_id_from_behavior(o.behavior) == id_bhvGokuNimbus and o.oAction < 3
        and o.oGokuOwner == network_global_index_from_local(m.playerIndex)
end

local function act_goku_nimbus_call(m)

    if not has_cloud(m) then
        goku_sound(m, "goku_lets_go.ogg")
        send_cloud(m, 0x2800, 1600, 1400)
    end
    goku_anim(m, "goku_nimbus_call")
    m.actionTimer = m.actionTimer + 1
    if m.pos.y > m.floorHeight + 4 then
        m.vel.y = math.max(m.vel.y - 2, -12)
        perform_air_step(m, 0)
    else
        mario_set_forward_vel(m, 0)
        perform_ground_step(m)
    end
    if m.actionTimer >= CALL_FRAMES then

        if m.playerIndex ~= 0 then
            m.actionTimer = CALL_FRAMES - 1
            return 0
        end
        m.vel.y = 30
        return set_mario_action(m, ACT_GOKU_NIMBUS, 0)
    end
    return 0
end

local function nimbus_clip(m, g)
    local speed = math.abs(m.forwardVel)
    if speed > 14 then g.nimbusFlying = true elseif speed < 8 then g.nimbusFlying = false end
    if g.nimbusFlying or math.abs(m.vel.y) > 3 then g.nimbusStill = 0 else g.nimbusStill = g.nimbusStill + 1 end
    if m.actionTimer < (g.nimbusFlying and CATCH + 2 or BOARD) then return "goku_nimbus_board" end
    if g.nimbusFlying then return "goku_nimbus_fly" end
    if g.nimbusStill > LIE_BACK then return "goku_nimbus_lie" end
    return g.nimbusStill > SIT_DOWN and "goku_nimbus_ride" or "goku_nimbus_stand"
end

local function act_goku_nimbus(m)
    local c = m.controller
    local g = gGoku[m.playerIndex]
    local mag = m.intendedMag / 32
    if m.actionTimer == 0 then g.nimbusStill, g.nimbusTurn, g.nimbusPitch, g.nimbusRoll = 0, 0, 0, 0 end

    if not has_cloud(m) then send_cloud(m, 0x8000, 500, 200) end
    goku_anim(m, nimbus_clip(m, g))

    local want = mag > 0.1 and wrap(m.intendedYaw - m.faceAngle.y) or 0
    g.nimbusTurn = approach_f32(g.nimbusTurn, math.max(-TURN, math.min(TURN, want * 0.3)), 0xA0, 0xA0)
    m.faceAngle.y = m.faceAngle.y + math.floor(g.nimbusTurn)
    m.forwardVel = approach_f32(m.forwardVel, SPEED * mag, 3, 2)
    local climb = 0
    if c.buttonDown & A_BUTTON ~= 0 then climb = CLIMB elseif c.buttonDown & Z_TRIG ~= 0 then climb = -CLIMB end
    m.vel.y = approach_f32(m.vel.y, climb, 3, 3)
    m.vel.x, m.vel.z = sins(m.faceAngle.y) * m.forwardVel, coss(m.faceAngle.y) * m.forwardVel
    m.peakHeight = m.pos.y

    local step = perform_air_step(m, 0)

    if step == AIR_STEP_LANDED and m.playerIndex == 0 then
        return set_mario_action(m, math.abs(m.forwardVel) > 16 and ACT_WALKING or ACT_IDLE, 0)
    end
    if m.playerIndex == 0 and c.buttonPressed & Y_BUTTON ~= 0 and m.actionTimer > 5 then
        g.nimbusLeft = get_global_timer()
        m.vel.y = 20
        return set_mario_action(m, ACT_FREEFALL, 0)
    end

    g.nimbusRest = math.max(0, (g.nimbusRest or 0) - 1)
    if m.forwardVel >= ZIP_AT and (g.nimbusWas or 0) < ZIP_AT and g.nimbusRest == 0 then
        goku_sound(m, "goku_nimbus.ogg", NIMBUS_GOES)
        g.nimbusRest = ZIP_REST
    end
    g.nimbusWas = m.forwardVel
    local speed = m.forwardVel / SPEED
    local roll = -g.nimbusTurn * 2.6 * math.min(math.abs(speed) * 2, 1) + sins(m.actionTimer * 0x300) * 0x200
    local climbing = m.actionTimer > CATCH and m.vel.y / CLIMB or 0
    local pitch = speed * 0x0700 - climbing * 0x0A00
    g.nimbusRoll = math.floor(g.nimbusRoll + (roll - g.nimbusRoll) * 0.14)
    g.nimbusPitch = math.floor(g.nimbusPitch + (pitch - g.nimbusPitch) * 0.14)
    local since = m.actionTimer - CATCH
    local give = since >= 0 and since < LANDING and sins(math.floor(since / LANDING * 0x8000)) * 15 or 0
    g.nimbusBob = sins(m.actionTimer * 0x500) * 6 - give
    local gfx = m.marioObj.header.gfx
    gfx.pos.y = m.pos.y + g.nimbusBob
    gfx.angle.x, gfx.angle.z = g.nimbusPitch, g.nimbusRoll
    m.actionTimer = m.actionTimer + 1
    return 0
end

local WING_LEAN = 0.5
function goku_wing_update(m)
    local flying = m.action == ACT_FLYING
    if not flying and m.action ~= ACT_FLYING_TRIPLE_JUMP then return end
    local g = gGoku[m.playerIndex]
    if not has_cloud(m) then

        if flying then send_cloud(m, 0x8000, 500, 200) else send_cloud(m, 0x2800, 1600, 1400) end
    end
    if flying then
        local gfx = m.marioObj.header.gfx
        g.nimbusPitch, g.nimbusRoll, g.nimbusBob = math.floor(gfx.angle.x * WING_LEAN), gfx.angle.z, 0
        gfx.angle.x = g.nimbusPitch
    end
end

hook_mario_action(ACT_GOKU_NIMBUS_CALL, {every_frame = act_goku_nimbus_call, gravity = function() end})
hook_mario_action(ACT_GOKU_NIMBUS, {every_frame = act_goku_nimbus, gravity = function() end})

local CALL_FROM = {
    [ACT_IDLE] = true, [ACT_WALKING] = true, [ACT_DECELERATING] = true, [ACT_BRAKING] = true, [ACT_PANTING] = true,
    [ACT_JUMP] = true, [ACT_DOUBLE_JUMP] = true, [ACT_TRIPLE_JUMP] = true, [ACT_FREEFALL] = true, [ACT_SIDE_FLIP] = true,
    [ACT_BACKFLIP] = true, [ACT_LONG_JUMP] = true, [ACT_WALL_KICK_AIR] = true, [ACT_JUMP_LAND] = true,
    [ACT_FREEFALL_LAND] = true,
}

function goku_nimbus_update(m)
    if m.playerIndex ~= 0 or m.controller.buttonPressed & Y_BUTTON == 0 then return end

    if gGoku[0].nimbusLeft == get_global_timer() then return end
    if CALL_FROM[m.action] and open_sky(m) then
        set_mario_action(m, ACT_GOKU_NIMBUS_CALL, 0)
    end
end
