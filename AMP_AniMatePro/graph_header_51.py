class GRAPH_HT_header(Header):
    bl_space_type = 'GRAPH_EDITOR'

    def draw(self, context):
        layout = self.layout
        tool_settings = context.tool_settings

        st = context.space_data

        layout.template_header()

        # Now a exposed as a sub-space type
        # layout.prop(st, "mode", text="")

        GRAPH_MT_editor_menus.draw_collapsible(context, layout)

        row = layout.row(align=True)
        row.prop(st, "use_normalization", icon='NORMALIZE_FCURVES', text="Normalize", toggle=True)
        sub = row.row(align=True)
        sub.active = st.use_normalization
        sub.prop(st, "use_auto_normalization", icon='FILE_REFRESH', text="", toggle=True)

        layout.separator_spacer()

        dopesheet_filter(layout, context)

        row = layout.row(align=True)
        if st.has_ghost_curves:
            row.operator("graph.ghost_curves_clear", text="", icon='X')
        else:
            row.operator("graph.ghost_curves_create", text="", icon='FCURVE_SNAPSHOT')

        layout.popover(
            panel="GRAPH_PT_filters",
            text="",
            icon='FILTER',
        )

        layout.prop(st, "pivot_point", icon_only=True)

        row = layout.row(align=True)
        if context.space_data.mode == 'DRIVERS':
            row.prop(tool_settings, "use_snap_driver", text="")
            sub = row.row(align=True)
            sub.popover(
                panel="GRAPH_PT_driver_snapping",
                text="",
            )
        else:
            row.prop(tool_settings, "use_snap_anim", text="")
            sub = row.row(align=True)
            sub.popover(
                panel="GRAPH_PT_snapping",
                text="",
            )

        row = layout.row(align=True)
        row.prop(tool_settings, "use_proportional_fcurve", text="", icon_only=True)
        sub = row.row(align=True)
        sub.active = tool_settings.use_proportional_fcurve
        sub.prop_with_popover(
            tool_settings,
            "proportional_edit_falloff",
            text="",
            icon_only=True,
            panel="GRAPH_PT_proportional_edit",
        )

