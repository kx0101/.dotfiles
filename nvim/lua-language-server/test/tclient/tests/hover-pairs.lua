local lclient   = require 'lclient'
local ws        = require 'workspace'
local await     = require 'await'

---@async
lclient():start(function (client)
    client:registerFakers()
    client:initialize()

    client:notify('textDocument/didOpen', {
        textDocument = {
            uri = 'file://test.lua',
            languageId = 'lua',
            version = 0,
            text = [[
local t ---@type table<string, number>
for key, value in pairs(t) do
    print(key, value) --key or value is unknown
end
]]
        }
    })

    ws.awaitReady()

    await.sleep(0.1)

    local hover1 = client:awaitRequest('textDocument/hover', {
        textDocument = { uri = 'file://test.lua' },
        position = { line = 2, character = 11 },
    })

    local hover2 = client:awaitRequest('textDocument/hover', {
        textDocument = { uri = 'file://test.lua' },
        position = { line = 2, character = 17 },
    })

    assert(hover1.contents.value:find 'string')
    assert(hover2.contents.value:find 'number')
end)
