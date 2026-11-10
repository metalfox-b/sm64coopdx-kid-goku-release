-- name: Kid Goku Dev
-- description: /wing puts the wing cap on, as picking one up does. Never in a release.

hook_chat_command("wing", "puts the wing cap on for its usual time", function()
    local m = gMarioStates[0]
    m.flags = m.flags | MARIO_WING_CAP
    m.capTimer = gLevelValues.wingCapDuration
    play_cap_music((4 << 8) | gLevelValues.wingCapSequence)
    return true
end)
