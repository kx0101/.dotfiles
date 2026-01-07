-- Automatically generated packer.nvim plugin loader code

if vim.api.nvim_call_function('has', {'nvim-0.5'}) ~= 1 then
  vim.api.nvim_command('echohl WarningMsg | echom "Invalid Neovim version for packer.nvim! | echohl None"')
  return
end

vim.api.nvim_command('packadd packer.nvim')

local no_errors, error_msg = pcall(function()

_G._packer = _G._packer or {}
_G._packer.inside_compile = true

local time
local profile_info
local should_profile = false
if should_profile then
  local hrtime = vim.loop.hrtime
  profile_info = {}
  time = function(chunk, start)
    if start then
      profile_info[chunk] = hrtime()
    else
      profile_info[chunk] = (hrtime() - profile_info[chunk]) / 1e6
    end
  end
else
  time = function(chunk, start) end
end

local function save_profiles(threshold)
  local sorted_times = {}
  for chunk_name, time_taken in pairs(profile_info) do
    sorted_times[#sorted_times + 1] = {chunk_name, time_taken}
  end
  table.sort(sorted_times, function(a, b) return a[2] > b[2] end)
  local results = {}
  for i, elem in ipairs(sorted_times) do
    if not threshold or threshold and elem[2] > threshold then
      results[i] = elem[1] .. ' took ' .. elem[2] .. 'ms'
    end
  end
  if threshold then
    table.insert(results, '(Only showing plugins that took longer than ' .. threshold .. ' ms ' .. 'to load)')
  end

  _G._packer.profile_output = results
end

time([[Luarocks path setup]], true)
local package_path_str = "/home/elijahkx/.cache/nvim/packer_hererocks/2.1.1741730670/share/lua/5.1/?.lua;/home/elijahkx/.cache/nvim/packer_hererocks/2.1.1741730670/share/lua/5.1/?/init.lua;/home/elijahkx/.cache/nvim/packer_hererocks/2.1.1741730670/lib/luarocks/rocks-5.1/?.lua;/home/elijahkx/.cache/nvim/packer_hererocks/2.1.1741730670/lib/luarocks/rocks-5.1/?/init.lua"
local install_cpath_pattern = "/home/elijahkx/.cache/nvim/packer_hererocks/2.1.1741730670/lib/lua/5.1/?.so"
if not string.find(package.path, package_path_str, 1, true) then
  package.path = package.path .. ';' .. package_path_str
end

if not string.find(package.cpath, install_cpath_pattern, 1, true) then
  package.cpath = package.cpath .. ';' .. install_cpath_pattern
end

time([[Luarocks path setup]], false)
time([[try_loadstring definition]], true)
local function try_loadstring(s, component, name)
  local success, result = pcall(loadstring(s), name, _G.packer_plugins[name])
  if not success then
    vim.schedule(function()
      vim.api.nvim_notify('packer.nvim: Error running ' .. component .. ' for ' .. name .. ': ' .. result, vim.log.levels.ERROR, {})
    end)
  end
  return result
end

time([[try_loadstring definition]], false)
time([[Defining packer_plugins]], true)
_G.packer_plugins = {
  ["99"] = {
    config = { "\27LJ\2\n*\0\0\2\1\1\0\4-\0\0\0009\0\0\0B\0\1\1K\0\1\0\0¿\21fill_in_function \0\0\2\1\1\0\4-\0\0\0009\0\0\0B\0\1\1K\0\1\0\0¿\vvisual+\0\0\2\1\1\0\4-\0\0\0009\0\0\0B\0\1\1K\0\1\0\0¿\22stop_all_requests≥\3\1\0\n\0\28\00016\0\0\0'\2\1\0B\0\2\0026\1\2\0009\1\3\0019\1\4\1B\1\1\0026\2\2\0009\2\5\0029\2\6\2\18\4\1\0B\2\2\0029\3\a\0005\5\b\0005\6\n\0009\a\t\0=\a\v\6'\a\f\0\18\b\2\0'\t\r\0&\a\t\a=\a\14\6=\6\15\0055\6\16\0=\6\17\5B\3\2\0016\3\2\0009\3\18\0039\3\19\3'\5\20\0'\6\21\0003\a\22\0B\3\4\0016\3\2\0009\3\18\0039\3\19\3'\5\23\0'\6\24\0003\a\25\0B\3\4\0016\3\2\0009\3\18\0039\3\19\3'\5\23\0'\6\26\0003\a\27\0B\3\4\0012\0\0ÄK\0\1\0\0\15<leader>9s\0\15<leader>9v\6v\0\15<leader>9f\6n\bset\vkeymap\rmd_files\1\2\0\0\rAGENT.md\vlogger\tpath\14.99.debug\n/tmp/\nlevel\1\0\3\tpath\0\19print_on_error\2\nlevel\0\nDEBUG\1\0\3\vlogger\0\rmd_files\0\nmodel\24opencode/gpt-5-nano\nsetup\rbasename\afs\bcwd\auv\bvim\a99\frequire\0" },
    loaded = true,
    path = "/home/elijahkx/.local/share/nvim/site/pack/packer/start/99",
    url = "https://github.com/ThePrimeagen/99"
  },
  LuaSnip = {
    loaded = true,
    path = "/home/elijahkx/.local/share/nvim/site/pack/packer/start/LuaSnip",
    url = "https://github.com/L3MON4D3/LuaSnip"
  },
  ["cmp-buffer"] = {
    loaded = true,
    path = "/home/elijahkx/.local/share/nvim/site/pack/packer/start/cmp-buffer",
    url = "https://github.com/hrsh7th/cmp-buffer"
  },
  ["cmp-nvim-lsp"] = {
    loaded = true,
    path = "/home/elijahkx/.local/share/nvim/site/pack/packer/start/cmp-nvim-lsp",
    url = "https://github.com/hrsh7th/cmp-nvim-lsp"
  },
  ["cmp-nvim-lua"] = {
    loaded = true,
    path = "/home/elijahkx/.local/share/nvim/site/pack/packer/start/cmp-nvim-lua",
    url = "https://github.com/hrsh7th/cmp-nvim-lua"
  },
  ["cmp-path"] = {
    loaded = true,
    path = "/home/elijahkx/.local/share/nvim/site/pack/packer/start/cmp-path",
    url = "https://github.com/hrsh7th/cmp-path"
  },
  cmp_luasnip = {
    loaded = true,
    path = "/home/elijahkx/.local/share/nvim/site/pack/packer/start/cmp_luasnip",
    url = "https://github.com/saadparwaiz1/cmp_luasnip"
  },
  ["diffview.nvim"] = {
    loaded = true,
    path = "/home/elijahkx/.local/share/nvim/site/pack/packer/start/diffview.nvim",
    url = "https://github.com/sindrets/diffview.nvim"
  },
  ["friendly-snippets"] = {
    loaded = true,
    path = "/home/elijahkx/.local/share/nvim/site/pack/packer/start/friendly-snippets",
    url = "https://github.com/rafamadriz/friendly-snippets"
  },
  ["gitsigns.nvim"] = {
    config = { "\27LJ\2\nQ\0\0\3\0\4\0\a6\0\0\0'\2\1\0B\0\2\0029\0\2\0005\2\3\0B\0\2\1K\0\1\0\1\0\1\23current_line_blame\2\nsetup\rgitsigns\frequire\0" },
    loaded = true,
    path = "/home/elijahkx/.local/share/nvim/site/pack/packer/start/gitsigns.nvim",
    url = "https://github.com/lewis6991/gitsigns.nvim"
  },
  ["gruber-darker.nvim"] = {
    config = { "\27LJ\2\nï\2\0\0\f\0\14\0\"6\0\0\0'\2\1\0B\0\2\0029\0\2\0B\0\1\0016\0\3\0009\0\4\0009\0\5\0'\2\1\0B\0\2\0015\0\6\0006\1\a\0\18\3\0\0B\1\2\4X\4\16Ä6\6\3\0009\6\b\0069\6\t\6)\b\0\0005\t\n\0=\5\v\tB\6\3\2+\a\1\0=\a\f\0066\a\3\0009\a\b\a9\a\r\a)\t\0\0\18\n\5\0\18\v\6\0B\a\4\1E\4\3\3R\4Ó\127K\0\1\0\16nvim_set_hl\vitalic\tname\1\0\1\tname\0\16nvim_get_hl\bapi\vipairs\1\4\0\0\vString\14Character\rConstant\16colorscheme\bcmd\bvim\nsetup\18gruber-darker\frequire\0" },
    loaded = true,
    path = "/home/elijahkx/.local/share/nvim/site/pack/packer/start/gruber-darker.nvim",
    url = "https://github.com/blazkowolf/gruber-darker.nvim"
  },
  harpoon = {
    loaded = true,
    path = "/home/elijahkx/.local/share/nvim/site/pack/packer/start/harpoon",
    url = "https://github.com/ThePrimeagen/harpoon"
  },
  ["lsp-zero.nvim"] = {
    loaded = true,
    path = "/home/elijahkx/.local/share/nvim/site/pack/packer/start/lsp-zero.nvim",
    url = "https://github.com/VonHeikemen/lsp-zero.nvim"
  },
  ["lualine.nvim"] = {
    loaded = true,
    path = "/home/elijahkx/.local/share/nvim/site/pack/packer/start/lualine.nvim",
    url = "https://github.com/nvim-lualine/lualine.nvim"
  },
  ["markdown-preview.nvim"] = {
    loaded = false,
    needs_bufread = false,
    only_cond = false,
    path = "/home/elijahkx/.local/share/nvim/site/pack/packer/opt/markdown-preview.nvim",
    url = "https://github.com/iamcco/markdown-preview.nvim"
  },
  ["mason-lspconfig.nvim"] = {
    loaded = true,
    path = "/home/elijahkx/.local/share/nvim/site/pack/packer/start/mason-lspconfig.nvim",
    url = "https://github.com/williamboman/mason-lspconfig.nvim"
  },
  ["mason.nvim"] = {
    loaded = true,
    path = "/home/elijahkx/.local/share/nvim/site/pack/packer/start/mason.nvim",
    url = "https://github.com/williamboman/mason.nvim"
  },
  ["move.vim"] = {
    loaded = true,
    path = "/home/elijahkx/.local/share/nvim/site/pack/packer/start/move.vim",
    url = "https://github.com/yanganto/move.vim"
  },
  ["neodev.nvim"] = {
    loaded = true,
    path = "/home/elijahkx/.local/share/nvim/site/pack/packer/start/neodev.nvim",
    url = "https://github.com/folke/neodev.nvim"
  },
  ["nvim-cmp"] = {
    loaded = true,
    path = "/home/elijahkx/.local/share/nvim/site/pack/packer/start/nvim-cmp",
    url = "https://github.com/hrsh7th/nvim-cmp"
  },
  ["nvim-comment"] = {
    config = { "\27LJ\2\n:\0\0\3\0\3\0\0066\0\0\0'\2\1\0B\0\2\0029\0\2\0B\0\1\1K\0\1\0\nsetup\17nvim_comment\frequire\0" },
    loaded = true,
    path = "/home/elijahkx/.local/share/nvim/site/pack/packer/start/nvim-comment",
    url = "https://github.com/terrortylor/nvim-comment"
  },
  ["nvim-dap"] = {
    loaded = true,
    path = "/home/elijahkx/.local/share/nvim/site/pack/packer/start/nvim-dap",
    url = "https://github.com/mfussenegger/nvim-dap"
  },
  ["nvim-dap-ui"] = {
    loaded = true,
    path = "/home/elijahkx/.local/share/nvim/site/pack/packer/start/nvim-dap-ui",
    url = "https://github.com/rcarriga/nvim-dap-ui"
  },
  ["nvim-jdtls"] = {
    loaded = true,
    path = "/home/elijahkx/.local/share/nvim/site/pack/packer/start/nvim-jdtls",
    url = "https://github.com/mfussenegger/nvim-jdtls"
  },
  ["nvim-lspconfig"] = {
    loaded = true,
    path = "/home/elijahkx/.local/share/nvim/site/pack/packer/start/nvim-lspconfig",
    url = "https://github.com/neovim/nvim-lspconfig"
  },
  ["nvim-nio"] = {
    loaded = true,
    path = "/home/elijahkx/.local/share/nvim/site/pack/packer/start/nvim-nio",
    url = "https://github.com/nvim-neotest/nvim-nio"
  },
  ["nvim-treesitter"] = {
    loaded = true,
    path = "/home/elijahkx/.local/share/nvim/site/pack/packer/start/nvim-treesitter",
    url = "https://github.com/nvim-treesitter/nvim-treesitter"
  },
  ["nvim-web-devicons"] = {
    config = { "\27LJ\2\nC\0\0\3\0\3\0\a6\0\0\0'\2\1\0B\0\2\0029\0\2\0004\2\0\0B\0\2\1K\0\1\0\nsetup\22nvim-web-devicons\frequire\0" },
    loaded = true,
    path = "/home/elijahkx/.local/share/nvim/site/pack/packer/start/nvim-web-devicons",
    url = "https://github.com/nvim-tree/nvim-web-devicons"
  },
  ["omnisharp-extended-lsp.nvim"] = {
    loaded = true,
    path = "/home/elijahkx/.local/share/nvim/site/pack/packer/start/omnisharp-extended-lsp.nvim",
    url = "https://github.com/Hoffs/omnisharp-extended-lsp.nvim"
  },
  ["packer.nvim"] = {
    config = { "\27LJ\2\nü\1\0\0\4\0\6\0\t6\0\0\0'\2\1\0B\0\2\0029\0\2\0005\2\4\0005\3\3\0=\3\5\2B\0\2\1K\0\1\0\15registries\1\0\1\15registries\0\1\3\0\0&github:Crashdummyy/mason-registry$github:mason-org/mason-registry\nsetup\nmason\frequire\0" },
    loaded = true,
    path = "/home/elijahkx/.local/share/nvim/site/pack/packer/start/packer.nvim",
    url = "https://github.com/wbthomason/packer.nvim"
  },
  playground = {
    loaded = true,
    path = "/home/elijahkx/.local/share/nvim/site/pack/packer/start/playground",
    url = "https://github.com/nvim-treesitter/playground"
  },
  ["plenary.nvim"] = {
    loaded = true,
    path = "/home/elijahkx/.local/share/nvim/site/pack/packer/start/plenary.nvim",
    url = "https://github.com/nvim-lua/plenary.nvim"
  },
  ["rose-pine"] = {
    loaded = true,
    path = "/home/elijahkx/.local/share/nvim/site/pack/packer/start/rose-pine",
    url = "https://github.com/rose-pine/neovim"
  },
  ["roslyn.nvim"] = {
    config = { "\27LJ\2\nü\2\0\2\a\0\15\0\0246\2\0\0'\4\1\0B\2\2\0029\2\2\2\18\4\0\0\18\5\1\0B\2\3\0019\2\3\0009\2\4\2\15\0\2\0X\3\fÄ6\2\5\0009\2\6\0029\2\a\0025\4\b\0005\5\t\0=\1\n\0056\6\5\0009\6\v\0069\6\f\0069\6\r\6=\6\14\5B\2\3\1K\0\1\0\rcallback\frefresh\rcodelens\blsp\vbuffer\1\0\2\vbuffer\0\rcallback\0\1\3\0\0\rBufEnter\17BufWritePost\24nvim_create_autocmd\bapi\bvim\21codeLensProvider\24server_capabilities\22default_on_attach\rlsp-zero\frequireØ\15\1\0\t\0)\00056\0\0\0'\2\1\0B\0\2\0029\0\2\0005\2\4\0003\3\3\0=\3\5\0026\3\0\0'\5\6\0B\3\2\0029\3\a\3B\3\1\2=\3\b\0025\3\t\0006\4\n\0009\4\v\0049\4\f\4'\6\r\0B\4\2\2'\5\14\0&\4\5\4>\4\2\3=\3\15\0025\3\16\0=\3\17\0026\3\0\0'\5\18\0B\3\2\0029\3\19\3'\5\20\0'\6\21\0'\a\22\0'\b\23\0B\3\5\2=\3\24\0025\3\26\0005\4\25\0=\4\27\0035\4\28\0=\4\29\0035\4\30\0=\4\31\0035\4!\0005\5 \0=\5\"\4=\4#\0035\4$\0=\4%\0035\4&\0=\4'\3=\3(\2B\0\2\1K\0\1\0\rsettings\22csharp|formatting\1\0\1&dotnet_organize_imports_on_format\2\25csharp|symbol_search\1\0\1'dotnet_search_reference_assemblies\2\31csharp|background_analysis\24background_analysis\1\0\1\24background_analysis\0\1\0\2&dotnet_compiler_diagnostics_scope\17fullSolution&dotnet_analyzer_diagnostics_scope\17fullSolution\22csharp|completion\1\0\3%dotnet_provide_regex_completions\2,dotnet_show_name_completion_suggestions\2<dotnet_show_completion_items_from_unimported_namespaces\2\21csharp|code_lens\1\0\2\"dotnet_enable_tests_code_lens\2'dotnet_enable_references_code_lens\2\23csharp|inlay_hints\1\0\6\21csharp|code_lens\0\31csharp|background_analysis\0\22csharp|formatting\0\25csharp|symbol_search\0\23csharp|inlay_hints\0\22csharp|completion\0\1\0\fHdotnet_suppress_inlay_hints_for_parameters_that_match_argument_name\2Jdotnet_suppress_inlay_hints_for_parameters_that_differ_only_by_suffix\2-dotnet_enable_inlay_hints_for_parameters\0023dotnet_enable_inlay_hints_for_other_parameters\2=dotnet_enable_inlay_hints_for_object_creation_parameters\0025dotnet_enable_inlay_hints_for_literal_parameters\0025dotnet_enable_inlay_hints_for_indexer_parameters\2(csharp_enable_inlay_hints_for_types\0029csharp_enable_inlay_hints_for_lambda_parameter_types\2:csharp_enable_inlay_hints_for_implicit_variable_types\2;csharp_enable_inlay_hints_for_implicit_object_creation\2Hdotnet_suppress_inlay_hints_for_parameters_that_match_method_intent\2\rroot_dir\t.git\r*.fsproj\r*.csproj\n*.sln\17root_pattern\19lspconfig.util\14filetypes\1\3\0\0\acs\avb\bcmdM/mason/packages/roslyn/libexec/Microsoft.CodeAnalysis.LanguageServer.dll\tdata\fstdpath\afn\bvim\1\5\0\0\vdotnet\0\27--logLevel=Information\f--stdio\17capabilities\21get_capabilities\rlsp-zero\14on_attach\1\0\t\16lock_target\2\14filetypes\0\14on_attach\0\17filewatching\boff\17capabilities\0\rroot_dir\0\rsettings\0\bcmd\0\17broad_search\1\0\nsetup\vroslyn\frequire\0" },
    loaded = false,
    needs_bufread = false,
    only_cond = false,
    path = "/home/elijahkx/.local/share/nvim/site/pack/packer/opt/roslyn.nvim",
    url = "https://github.com/seblyng/roslyn.nvim"
  },
  ["rust-tools.nvim"] = {
    loaded = true,
    path = "/home/elijahkx/.local/share/nvim/site/pack/packer/start/rust-tools.nvim",
    url = "https://github.com/simrat39/rust-tools.nvim"
  },
  ["telescope-file-browser.nvim"] = {
    loaded = true,
    path = "/home/elijahkx/.local/share/nvim/site/pack/packer/start/telescope-file-browser.nvim",
    url = "https://github.com/nvim-telescope/telescope-file-browser.nvim"
  },
  ["telescope.nvim"] = {
    loaded = true,
    path = "/home/elijahkx/.local/share/nvim/site/pack/packer/start/telescope.nvim",
    url = "https://github.com/nvim-telescope/telescope.nvim"
  },
  undotree = {
    loaded = true,
    path = "/home/elijahkx/.local/share/nvim/site/pack/packer/start/undotree",
    url = "https://github.com/mbbill/undotree"
  },
  ["vim-floaterm"] = {
    loaded = true,
    path = "/home/elijahkx/.local/share/nvim/site/pack/packer/start/vim-floaterm",
    url = "https://github.com/voldikss/vim-floaterm"
  },
  ["vim-fugitive"] = {
    loaded = true,
    path = "/home/elijahkx/.local/share/nvim/site/pack/packer/start/vim-fugitive",
    url = "https://github.com/tpope/vim-fugitive"
  }
}

time([[Defining packer_plugins]], false)
-- Setup for: markdown-preview.nvim
time([[Setup for markdown-preview.nvim]], true)
try_loadstring("\27LJ\2\n=\0\0\2\0\4\0\0056\0\0\0009\0\1\0005\1\3\0=\1\2\0K\0\1\0\1\2\0\0\rmarkdown\19mkdp_filetypes\6g\bvim\0", "setup", "markdown-preview.nvim")
time([[Setup for markdown-preview.nvim]], false)
-- Config for: nvim-comment
time([[Config for nvim-comment]], true)
try_loadstring("\27LJ\2\n:\0\0\3\0\3\0\0066\0\0\0'\2\1\0B\0\2\0029\0\2\0B\0\1\1K\0\1\0\nsetup\17nvim_comment\frequire\0", "config", "nvim-comment")
time([[Config for nvim-comment]], false)
-- Config for: 99
time([[Config for 99]], true)
try_loadstring("\27LJ\2\n*\0\0\2\1\1\0\4-\0\0\0009\0\0\0B\0\1\1K\0\1\0\0¿\21fill_in_function \0\0\2\1\1\0\4-\0\0\0009\0\0\0B\0\1\1K\0\1\0\0¿\vvisual+\0\0\2\1\1\0\4-\0\0\0009\0\0\0B\0\1\1K\0\1\0\0¿\22stop_all_requests≥\3\1\0\n\0\28\00016\0\0\0'\2\1\0B\0\2\0026\1\2\0009\1\3\0019\1\4\1B\1\1\0026\2\2\0009\2\5\0029\2\6\2\18\4\1\0B\2\2\0029\3\a\0005\5\b\0005\6\n\0009\a\t\0=\a\v\6'\a\f\0\18\b\2\0'\t\r\0&\a\t\a=\a\14\6=\6\15\0055\6\16\0=\6\17\5B\3\2\0016\3\2\0009\3\18\0039\3\19\3'\5\20\0'\6\21\0003\a\22\0B\3\4\0016\3\2\0009\3\18\0039\3\19\3'\5\23\0'\6\24\0003\a\25\0B\3\4\0016\3\2\0009\3\18\0039\3\19\3'\5\23\0'\6\26\0003\a\27\0B\3\4\0012\0\0ÄK\0\1\0\0\15<leader>9s\0\15<leader>9v\6v\0\15<leader>9f\6n\bset\vkeymap\rmd_files\1\2\0\0\rAGENT.md\vlogger\tpath\14.99.debug\n/tmp/\nlevel\1\0\3\tpath\0\19print_on_error\2\nlevel\0\nDEBUG\1\0\3\vlogger\0\rmd_files\0\nmodel\24opencode/gpt-5-nano\nsetup\rbasename\afs\bcwd\auv\bvim\a99\frequire\0", "config", "99")
time([[Config for 99]], false)
-- Config for: gruber-darker.nvim
time([[Config for gruber-darker.nvim]], true)
try_loadstring("\27LJ\2\nï\2\0\0\f\0\14\0\"6\0\0\0'\2\1\0B\0\2\0029\0\2\0B\0\1\0016\0\3\0009\0\4\0009\0\5\0'\2\1\0B\0\2\0015\0\6\0006\1\a\0\18\3\0\0B\1\2\4X\4\16Ä6\6\3\0009\6\b\0069\6\t\6)\b\0\0005\t\n\0=\5\v\tB\6\3\2+\a\1\0=\a\f\0066\a\3\0009\a\b\a9\a\r\a)\t\0\0\18\n\5\0\18\v\6\0B\a\4\1E\4\3\3R\4Ó\127K\0\1\0\16nvim_set_hl\vitalic\tname\1\0\1\tname\0\16nvim_get_hl\bapi\vipairs\1\4\0\0\vString\14Character\rConstant\16colorscheme\bcmd\bvim\nsetup\18gruber-darker\frequire\0", "config", "gruber-darker.nvim")
time([[Config for gruber-darker.nvim]], false)
-- Config for: packer.nvim
time([[Config for packer.nvim]], true)
try_loadstring("\27LJ\2\nü\1\0\0\4\0\6\0\t6\0\0\0'\2\1\0B\0\2\0029\0\2\0005\2\4\0005\3\3\0=\3\5\2B\0\2\1K\0\1\0\15registries\1\0\1\15registries\0\1\3\0\0&github:Crashdummyy/mason-registry$github:mason-org/mason-registry\nsetup\nmason\frequire\0", "config", "packer.nvim")
time([[Config for packer.nvim]], false)
-- Config for: gitsigns.nvim
time([[Config for gitsigns.nvim]], true)
try_loadstring("\27LJ\2\nQ\0\0\3\0\4\0\a6\0\0\0'\2\1\0B\0\2\0029\0\2\0005\2\3\0B\0\2\1K\0\1\0\1\0\1\23current_line_blame\2\nsetup\rgitsigns\frequire\0", "config", "gitsigns.nvim")
time([[Config for gitsigns.nvim]], false)
-- Config for: nvim-web-devicons
time([[Config for nvim-web-devicons]], true)
try_loadstring("\27LJ\2\nC\0\0\3\0\3\0\a6\0\0\0'\2\1\0B\0\2\0029\0\2\0004\2\0\0B\0\2\1K\0\1\0\nsetup\22nvim-web-devicons\frequire\0", "config", "nvim-web-devicons")
time([[Config for nvim-web-devicons]], false)
vim.cmd [[augroup packer_load_aucmds]]
vim.cmd [[au!]]
  -- Filetype lazy-loads
time([[Defining lazy-load filetype autocommands]], true)
vim.cmd [[au FileType markdown ++once lua require("packer.load")({'markdown-preview.nvim'}, { ft = "markdown" }, _G.packer_plugins)]]
vim.cmd [[au FileType cs ++once lua require("packer.load")({'roslyn.nvim'}, { ft = "cs" }, _G.packer_plugins)]]
time([[Defining lazy-load filetype autocommands]], false)
vim.cmd("augroup END")

_G._packer.inside_compile = false
if _G._packer.needs_bufread == true then
  vim.cmd("doautocmd BufRead")
end
_G._packer.needs_bufread = false

if should_profile then save_profiles() end

end)

if not no_errors then
  error_msg = error_msg:gsub('"', '\\"')
  vim.api.nvim_command('echohl ErrorMsg | echom "Error in packer_compiled: '..error_msg..'" | echom "Please check your config for correctness" | echohl None')
end
