class DOPESHEET_HT_header(Header):
    bl_space_type = 'DOPESHEET_EDITOR'

    def draw(self, context):
        layout = self.layout

        st = context.space_data

        layout.template_header()

        if st.mode != 'TIMELINE':
            # Timeline mode is special, as it's presented as a sub-type of the
            # dope sheet editor, rather than a mode. So this shouldn't show the
            # mode selector.
            layout.prop(st, "ui_mode", text="")

        DOPESHEET_MT_editor_menus.draw_collapsible(context, layout)
        DOPESHEET_HT_editor_buttons.draw_header(context, layout)


# Header for "normal" dopesheet editor modes (e.g. Dope Sheet, Action, Shape Keys, etc.)