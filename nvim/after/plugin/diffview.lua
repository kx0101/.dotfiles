require("diffview").setup({
    enhanced_diff_hl = true,
    use_icons = true,
    signs = {
        fold_closed = "",
        fold_open = "",
    },
    file_panel = {
        listing_style = "tree",
        tree_options = {
            flatten_dirs = true,
            folder_statuses = "only_folded",
        },
    },
})
