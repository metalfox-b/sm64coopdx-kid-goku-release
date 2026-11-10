if not _G.charSelectExists then return end

local DETERMINED, SHOUT, SURPRISED, HAPPY = MARIO_EYES_LOOK_LEFT, MARIO_EYES_LOOK_RIGHT, MARIO_EYES_LOOK_UP,
    MARIO_EYES_LOOK_DOWN
local BLINK_HALF, BLINK_SHUT, SMILE, CHEER = 9, 10, 11, 16

local GRIT, FIERCE, YELL, HIT, GRIN = DETERMINED, DETERMINED, 14, SURPRISED, DETERMINED

local YELL_LEFT, YELL_RIGHT = YELL, YELL
GOKU_FACES = {grit = GRIT, fierce = FIERCE, yell = YELL, hit = HIT, grin = GRIN}

local FACE = {
    [ACT_MOVE_PUNCHING] = GRIT, [ACT_JUMP_KICK] = GRIT, [ACT_DIVE] = YELL, [ACT_DIVE_SLIDE] = GRIN,
    [ACT_SLIDE_KICK] = GRIT, [ACT_GROUND_POUND] = GRIT, [ACT_GROUND_POUND_LAND] = GRIT, [ACT_PICKING_UP_BOWSER] = DETERMINED, [ACT_HOLDING_BOWSER] = DETERMINED,
    [ACT_RELEASING_BOWSER] = SHOUT, [ACT_TRIPLE_JUMP] = SHOUT, [ACT_LONG_JUMP] = HAPPY,
    [ACT_HARD_BACKWARD_GROUND_KB] = HIT, [ACT_HARD_FORWARD_GROUND_KB] = HIT,
    [ACT_BACKWARD_GROUND_KB] = HIT, [ACT_FORWARD_GROUND_KB] = HIT,
    [ACT_SOFT_BACKWARD_GROUND_KB] = HIT, [ACT_SOFT_FORWARD_GROUND_KB] = HIT,
    [ACT_HARD_BACKWARD_AIR_KB] = HIT, [ACT_HARD_FORWARD_AIR_KB] = HIT,
    [ACT_BACKWARD_AIR_KB] = HIT, [ACT_FORWARD_AIR_KB] = HIT, [ACT_THROWN_BACKWARD] = HIT,
    [ACT_THROWN_FORWARD] = HIT, [ACT_BURNING_JUMP] = HIT, [ACT_BURNING_FALL] = HIT,
    [ACT_BURNING_GROUND] = HIT, [ACT_LAVA_BOOST] = HIT, [ACT_SHOCKED] = HIT,
    [ACT_GETTING_BLOWN] = SURPRISED, [ACT_SQUISHED] = HIT,
    [ACT_STAR_DANCE_EXIT] = CHEER, [ACT_STAR_DANCE_NO_EXIT] = CHEER, [ACT_STAR_DANCE_WATER] = CHEER,
    [ACT_JUMBO_STAR_CUTSCENE] = CHEER,
    [ACT_GOKU_NIMBUS_CALL] = SHOUT,
    [ACT_SLEEPING] = BLINK_SHUT,
    [ACT_GROUND_BONK] = HIT, [ACT_SOFT_BONK] = HIT, [ACT_START_CROUCHING] = DETERMINED,
    [ACT_CROUCHING] = DETERMINED, [ACT_STOP_CROUCHING] = DETERMINED, [ACT_HOLD_IDLE] = SMILE,
    [ACT_HOLD_HEAVY_IDLE] = DETERMINED, [ACT_HOLD_HEAVY_WALKING] = DETERMINED, [ACT_WATER_IDLE] = SMILE,
    [ACT_HOLD_WATER_IDLE] = SMILE,
}

local KIND = {[ACT_GROUP_AIRBORNE] = HAPPY, [ACT_GROUP_SUBMERGED] = DETERMINED, [ACT_GROUP_AUTOMATIC] = DETERMINED,
    [ACT_GROUP_OBJECT] = DETERMINED}

local RUN_FROM, WALK_FROM = 22, 18

local FACE_HOLD = 14

local GRINS_ON = {[ACT_PUNCHING] = true, [ACT_MOVE_PUNCHING] = true, [ACT_JUMP_KICK] = true, [ACT_DIVE] = true, [ACT_DIVE_SLIDE] = true,
    [ACT_IDLE] = true, [ACT_FREEFALL] = true, [ACT_FREEFALL_LAND] = true}

local function busy_face(m, g)
    local kind = m.action & ACT_GROUP_MASK
    if kind ~= ACT_GROUP_MOVING and m.action ~= ACT_GOKU_NIMBUS then return KIND[kind] end
    local speed = math.abs(m.forwardVel)
    if speed > RUN_FROM then g.grinning = true elseif speed < WALK_FROM then g.grinning = false end
    return g.grinning and HAPPY or SMILE
end

local BLINK = {BLINK_HALF, BLINK_SHUT, BLINK_SHUT, BLINK_SHUT, BLINK_HALF}
local BLINK_SOON, BLINK_LATE = 75, 180

local function resting_eyes(g)
    g.blinkWait = (g.blinkWait or math.random(BLINK_SOON, BLINK_LATE)) - 1
    if g.blinkWait > 0 then return MARIO_EYES_OPEN end
    local step = BLINK[1 - g.blinkWait]
    if step then return step end

    g.blinkWait = math.random(6) == 1 and 5 or math.random(BLINK_SOON, BLINK_LATE)
    return MARIO_EYES_OPEN
end

function goku_face_update(m)
    local g = gGoku[m.playerIndex]
    local body = m.marioBodyState
    local face = FACE[m.action]
    if m.action == ACT_GOKU_KAME then
        face = m.actionState == 0 and DETERMINED or SHOUT
    elseif m.action == ACT_PUNCHING then
        face = m.actionArg >= 6 and YELL or GRIT
    elseif m.action == ACT_MOVE_PUNCHING and g.lastAction ~= ACT_PUNCHING and not g.punchLanded then
        face = m.actionArg >= 3 and YELL_RIGHT or YELL_LEFT
    elseif m.action == ACT_FREEFALL and m.vel.y < -60 then
        face = SURPRISED
    elseif m.action == ACT_IDLE and (g.ready or 0) > 0 then
        face = FIERCE
    elseif m.action == ACT_GOKU_NIMBUS and m.actionTimer > 8 and m.actionTimer < 56 then
        face = MARIO_EYES_CLOSED
    elseif m.action == ACT_START_SLEEPING and m.actionState == 2 then
        face = MARIO_EYES_CLOSED
    end
    if (g.stompLeft or 0) > 0 then face = HAPPY end

    if (g.grinFor or 0) > 0 then
        g.grinFor = g.grinFor - 1
        if GRINS_ON[m.action] then face = GRIN end
    end

    if not face and body.eyeState == MARIO_EYES_BLINK then face = busy_face(m, g) end
    if face then
        g.face, g.faceHold = face, FACE_HOLD
        if body.eyeState ~= MARIO_EYES_DEAD then body.eyeState = face end
    elseif body.eyeState == MARIO_EYES_BLINK then
        if g.faceHold > 0 then
            g.faceHold = g.faceHold - 1
            body.eyeState = g.face
        else
            body.eyeState = resting_eyes(g)
        end
    end
end
