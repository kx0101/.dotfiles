local M = {}

function M:setup()
    local project_name = vim.fn.fnamemodify(vim.fn.getcwd(), ":p:h:t")
    local workspace_dir = vim.fn.stdpath("data") ..
        package.config:sub(1, 1) .. "jdtls-workspace" .. package.config:sub(1, 1) .. project_name
    local os_name = vim.loop.os_uname().sysname

    -- jdtls >= 1.34 requires JDK 21+ to run. On Windows the default `java` on PATH
    -- may be older (e.g. JDK 17), so prefer an installed JDK 21 if one is present.
    local java_cmd = "java"
    if vim.fn.has("win32") == 1 then
        local jdk21 = vim.fn.glob("C:/Program Files/Microsoft/jdk-21*/bin/java.exe", true, true)
        if #jdk21 == 0 then
            jdk21 = vim.fn.glob("C:/Program Files/Eclipse Adoptium/jdk-21*/bin/java.exe", true, true)
        end
        if #jdk21 > 0 then
            java_cmd = jdk21[1]
        end
    end

    local config = {
        cmd = {

            java_cmd,

            "-Declipse.application=org.eclipse.jdt.ls.core.id1",
            "-Dosgi.bundles.defaultStartLevel=4",
            "-Declipse.product=org.eclipse.jdt.ls.core.product",
            "-Dlog.protocol=true",
            "-Dlog.level=ALL",
            "-Xmx1g",
            "--add-modules=ALL-SYSTEM",
            "--add-opens",
            "java.base/java.util=ALL-UNNAMED",
            "--add-opens",
            "java.base/java.lang=ALL-UNNAMED",

            "-jar",
            vim.fn.glob(vim.fn.stdpath("data") ..
                package.config:sub(1, 1) ..
                "mason" ..
                package.config:sub(1, 1) ..
                "packages" ..
                package.config:sub(1, 1) ..
                "jdtls" ..
                package.config:sub(1, 1) ..
                "plugins" .. package.config:sub(1, 1) .. "org.eclipse.equinox.launcher_*.jar"),
            "-configuration",
            vim.fn.stdpath("data") ..
            package.config:sub(1, 1) ..
            "mason" ..
            package.config:sub(1, 1) ..
            "packages" ..
            package.config:sub(1, 1) ..
            "jdtls" ..
            package.config:sub(1, 1) ..
            "config_" .. (os_name == "Windows_NT" and "win" or os_name == "Linux" and "linux" or "mac"),

            "-data",
            workspace_dir,
        },

        root_dir = require("jdtls.setup").find_root({ ".git", "mvnw", "gradlew", "pom.xml" }),

        settings = {
            java = {},
        },

        init_options = {
            bundles = {},
        },
    }

    require("jdtls").start_or_attach(config)
end

return M
