# BlenderBIM Add-on - OpenBIM Blender Add-on
# Copyright (C) 2020, 2021 Dion Moult <dion@thinkmoult.com>
#
# This file is part of BlenderBIM Add-on.
#
# BlenderBIM Add-on is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# BlenderBIM Add-on is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with BlenderBIM Add-on.  If not, see <http://www.gnu.org/licenses/>.

import os
import bpy
import addon_utils
from pathlib import Path
from bpy.types import Panel
from bpy.props import StringProperty, IntProperty, BoolProperty
from ifcopenshell.util.doc import (
    get_entity_doc,
    get_property_set_doc,
    get_type_doc,
    get_attribute_doc,
)
from . import ifc
import blenderbim.tool as tool
import blenderbim.bim
from blenderbim.bim.helper import IfcHeaderExtractor
from blenderbim.bim.prop import Attribute


class IFCFileSelector:
    def is_existing_ifc_file(self, filepath=None):
        if filepath is None:
            filepath = self.filepath
        return os.path.exists(filepath) and "ifc" in os.path.splitext(filepath)[1].lower()

    def get_filepath(self):
        """get filepath taking into account relative paths"""
        if self.use_relative_path:
            filepath = os.path.relpath(self.filepath, bpy.path.abspath("//"))
        else:
            filepath = self.filepath
        return filepath

    def draw(self, context):
        # Access filepath & Directory https://blender.stackexchange.com/a/207665
        params = context.space_data.params
        # Decode byte string https://stackoverflow.com/a/47737082/
        directory = Path(params.directory.decode("utf-8"))
        filepath = os.path.join(directory, params.filename)
        layout = self.layout
        if self.is_existing_ifc_file(filepath):
            box = layout.box()
            box.label(text="IFC Header Specifications", icon="INFO")
            header_data = IfcHeaderExtractor(filepath).extract()
            for key, value in header_data.items():
                if value != "":
                    split = box.split()
                    split.label(text=key.title().replace("_", " "))
                    split.label(text=str(value))
                    if key.lower() == "schema_name" and filepath[-4:].lower() == ".ifc":
                        schema_lower = str(value).lower()
                        if schema_lower == "ifc2x3":
                            row = box.row()
                            op = row.operator("bim.run_migrate_patch", text="Upgrade to IFC4")
                            op.infile = filepath
                            op.outfile = filepath[0:-4] + "-IFC4.ifc"
                            op.schema = "IFC4"
                        elif schema_lower == "ifc4":
                            row = box.row()
                            op = row.operator("bim.run_migrate_patch", text="Upgrade to IFC4X3")
                            op.infile = filepath
                            op.outfile = filepath[0:-4] + "-IFC4X3.ifc"
                            op.schema = "IFC4X3"

        if bpy.data.is_saved:
            layout.prop(self, "use_relative_path")
        else:
            self.use_relative_path = False
            layout.label(text="Save the .blend file first ")
            layout.label(text="to use relative paths for .ifc.")


class BIM_PT_section_plane(Panel):
    bl_label = "Temporary Section Cutaways"
    bl_idname = "BIM_PT_section_plane"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "output"
    bl_options = {"DEFAULT_CLOSED"}
    bl_parent_id = "BIM_PT_tab_sandbox"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        props = context.scene.BIMProperties

        layout.prop(props, "should_section_selected_objects")
        layout.prop(props, "section_plane_colour")
        layout.prop(props, "section_line_decorator_width")

        row = layout.row(align=True)
        row.operator("bim.add_section_plane")
        row.operator("bim.remove_section_plane")


class BIM_PT_section_with_cappings(Panel):
    bl_label = "Section Cutaways With Cappings"
    bl_idname = "BIM_PT_section_with_cappings"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "output"
    bl_options = {"DEFAULT_CLOSED"}
    bl_parent_id = "BIM_PT_tab_sandbox"

    def draw(self, context):
        layout = self.layout
        wm = context.window_manager
        row = layout.row(align=True)
        row.operator("bim.clipping_plane_cut_with_cappings", icon="XRAY", text="Cut")
        row.operator("bim.revert_clipping_plane_cut", icon="FILE_REFRESH", text="Revert Cut")

        props = context.scene.BIMProjectProperties
        box = layout.box()
        header = box.row(align=True)
        header.label(text="Clipping Planes")
        header.operator("bim.save_clipping_planes", text="", icon="EXPORT")
        header.operator("bim.load_clipping_planes", text="", icon="IMPORT")
        header.operator("bim.create_clipping_plane", text="", icon="ADD")

        box.template_list(
            "BIM_UL_clipping_plane",
            "",
            props,
            "clipping_planes",
            props,
            "clipping_planes_active",
        )

        if props.clipping_planes_active < len(props.clipping_planes):
            active_clipping_plane_obj = props.clipping_planes[props.clipping_planes_active].obj
            box.prop(active_clipping_plane_obj, "location")
            box.prop(active_clipping_plane_obj, "rotation_euler")


class BIM_UL_clipping_plane(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if item and item.obj:
            obj = item.obj
            row = layout.row(align=True)
            row.prop(obj, "name", text="", emboss=False)
            row.operator("bim.select_object", text="", icon="RESTRICT_SELECT_OFF").obj_name = obj.name
            row.context_pointer_set("active_object", obj)
            row.operator("bim.flip_clipping_plane", text="", icon="PASTEFLIPDOWN")
            row.operator("bim.delete_object", text="", icon="TRASH").obj_name = obj.name
        else:
            layout.label(text="", translate=False)


class BIM_UL_generic(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if item:
            layout.prop(item, "name", text="", emboss=False)
        else:
            layout.label(text="", translate=False)


class BIM_UL_topics(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        ob = data
        if item:
            layout.prop(item, "title", text="", emboss=False)
        else:
            layout.label(text="", translate=False)


class BIM_ADDON_preferences(bpy.types.AddonPreferences):
    bl_idname = "blenderbim"
    svg2pdf_command: StringProperty(name="SVG to PDF Command", description='E.g. [["inkscape", "svg", "-o", pdf]]')
    svg2dxf_command: StringProperty(
        name="SVG to DXF Command",
        description='E.g. [["inkscape", "svg", "-o", "eps"], ["pstoedit", "-dt", "-f", "dxf:-polyaslines -mm", "eps", "dxf", "-psarg", "-dNOSAFER"]]',
    )
    svg_command: StringProperty(name="SVG Command", description='E.g. [["firefox", "path"]]')
    layout_svg_command: StringProperty(name="Layout SVG Command", description='E.g. [["firefox", "path"]]')
    pdf_command: StringProperty(name="PDF Command", description='E.g. [["firefox", "path"]]')
    spreadsheet_command: StringProperty(name="Spreadsheet Command", description='E.g. [["libreoffice", "path"]]')
    openlca_port: IntProperty(name="OpenLCA IPC Port", default=8080)
    should_hide_empty_props: BoolProperty(name="Should Hide Empty Properties", default=True)
    should_setup_workspace: BoolProperty(name="Should Setup Workspace Layout for BIM", default=True)
    should_setup_toolbar: BoolProperty(
        name="Always Show Toolbar In 3D Viewport",
        default=True,
        description="If disabled, the toolbar will only load when an IFC model is active",
    )
    should_play_chaching_sound: BoolProperty(
        name="Should Make A Cha-Ching Sound When Project Costs Updates", default=False
    )
    lock_grids_on_import: BoolProperty(name="Should Lock Grids By Default", default=True)
    spatial_elements_unselectable: BoolProperty(name="Should Make Spatial Elements Unselectable By Default", default=True)
    decorations_colour: bpy.props.FloatVectorProperty(
        name="Decorations Colour", subtype="COLOR", default=(1, 1, 1, 1), min=0.0, max=1.0, size=4
    )
    decorator_color_selected: bpy.props.FloatVectorProperty(
        name="Selected Elements Color",
        subtype="COLOR",
        default=(0.545, 0.863, 0, 1),  # green
        min=0.0,
        max=1.0,
        size=4,
        description="Color of selected verts/edges (used in profile editing mode)",
    )
    decorator_color_unselected: bpy.props.FloatVectorProperty(
        name="Not Selected Elements Color",
        subtype="COLOR",
        default=(1, 1, 1, 1),  # white
        min=0.0,
        max=1.0,
        size=4,
        description="Color of not selected verts/edges (used in profile editing mode)",
    )
    decorator_color_special: bpy.props.FloatVectorProperty(
        name="Special Elements Color",
        subtype="COLOR",
        default=(0.157, 0.565, 1, 1),  # blue
        min=0.0,
        max=1.0,
        size=4,
        description="Color of special selected verts/edges (openings, preview verts/edges in roof editing, verts with arcs/circles in profile editing)",
    )

    def draw(self, context):
        layout = self.layout

        box = layout.box()
        row = box.row()
        row.label(
            text="To uninstall: 1) Disable the add-on 2) Restart Blender 3) Press the 'Remove' button.",
            icon="ERROR",
        )
        row = box.row()
        row.label(
            text="To upgrade, first uninstall your current BlenderBIM Add-on, then install the new version.",
            icon="ERROR",
        )

        row = layout.row()
        row.operator("bim.open_upstream", text="Help Donate to Fund Development!", icon="FUND").page = "fund"
        row = layout.row()
        row.operator("bim.open_upstream", text="Visit Homepage").page = "home"
        row.operator("bim.open_upstream", text="Visit Documentation").page = "docs"
        row = layout.row()
        row.operator("bim.open_upstream", text="Visit Wiki").page = "wiki"
        row.operator("bim.open_upstream", text="Visit Community").page = "community"
        row = layout.row()
        row.operator("bim.file_associate", icon="LOCKVIEW_ON")
        row.operator("bim.file_unassociate", icon="LOCKVIEW_OFF")
        row = layout.row()
        row.prop(self, "svg2pdf_command")
        row = layout.row()
        row.prop(self, "svg2dxf_command")
        row = layout.row()
        row.prop(self, "svg_command")
        row = layout.row()
        row.prop(self, "layout_svg_command")
        row = layout.row()
        row.prop(self, "pdf_command")
        row = layout.row()
        row.prop(self, "spreadsheet_command")
        row = layout.row()
        row.prop(self, "openlca_port")
        row = layout.row()
        row.prop(self, "should_hide_empty_props")
        row = layout.row()
        row.prop(self, "should_setup_workspace")
        row = layout.row()
        row.prop(self, "should_setup_toolbar")
        row = layout.row()
        row.prop(self, "should_play_chaching_sound")
        row = layout.row()
        row.prop(self, "lock_grids_on_import")
        row = layout.row()
        row.prop(self, "spatial_elements_unselectable")



        row = layout.row()
        row.prop(context.scene.BIMProjectProperties, "should_disable_undo_on_save")
        row = layout.row()
        row.prop(context.scene.BIMProjectProperties, "should_stream")

        row = layout.row()
        row.prop(context.scene.BIMModelProperties, "occurrence_name_style")
        if context.scene.BIMModelProperties == "CUSTOM":
            row = layout.row()
            row.prop(context.scene.BIMModelProperties, "occurrence_name_function")

        row = self.layout.row()
        row.prop(self, "decorations_colour")
        row = self.layout.row()
        row.prop(self, "decorator_color_selected")
        row = self.layout.row()
        row.prop(self, "decorator_color_unselected")
        row = self.layout.row()
        row.prop(self, "decorator_color_special")

        row = self.layout.row(align=True)
        row.prop(context.scene.BIMProperties, "schema_dir")
        row.operator("bim.select_schema_dir", icon="FILE_FOLDER", text="")

        row = self.layout.row(align=True)
        row.prop(context.scene.BIMProperties, "data_dir")
        row.operator("bim.select_data_dir", icon="FILE_FOLDER", text="")

        row = self.layout.row(align=True)
        row.prop(context.scene.BIMProperties, "pset_dir")
        row = self.layout.row(align=True)
        row.prop(context.scene.DocProperties, "sheets_dir")
        row = self.layout.row(align=True)
        row.prop(context.scene.DocProperties, "layouts_dir")
        row = self.layout.row(align=True)
        row.prop(context.scene.DocProperties, "titleblocks_dir")
        row = self.layout.row(align=True)
        row.prop(context.scene.DocProperties, "drawings_dir")
        row = self.layout.row(align=True)
        row.prop(context.scene.DocProperties, "stylesheet_path")
        row = self.layout.row(align=True)
        row.prop(context.scene.DocProperties, "markers_path")
        row = self.layout.row(align=True)
        row.prop(context.scene.DocProperties, "symbols_path")
        row = self.layout.row(align=True)
        row.prop(context.scene.DocProperties, "patterns_path")
        row = self.layout.row(align=True)
        row.prop(context.scene.DocProperties, "shadingstyles_path")
        row = self.layout.row(align=True)
        row.prop(context.scene.DocProperties, "shadingstyle_default")


# Scene panel groups
class BIM_PT_tabs(Panel):
    bl_label = "BlenderBIM Add-on"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_order = 0
    bl_options = {"HIDE_HEADER"}

    def draw(self, context):
        try:
            is_ifc_project = bool(tool.Ifc.get())
            aprops = tool.Blender.get_area_props(context)
            if not aprops:
                # Fallback in case areas aren't setup yet.
                aprops = context.screen.BIMTabProperties

            row = self.layout.row()
            row.operator(
                "bim.set_tab",
                text="",
                emboss=aprops.tab == "PROJECT",
                depress=True,
                icon_value=blenderbim.bim.icons["IFC"].icon_id,
            ).tab = "PROJECT"
            self.draw_tab_entry(row, "FILE_3D", "OBJECT", is_ifc_project, aprops.tab == "OBJECT")
            self.draw_tab_entry(row, "MATERIAL", "GEOMETRY", is_ifc_project, aprops.tab == "GEOMETRY")
            self.draw_tab_entry(row, "DOCUMENTS", "DRAWINGS", is_ifc_project, aprops.tab == "DRAWINGS")
            self.draw_tab_entry(row, "NETWORK_DRIVE", "SERVICES", is_ifc_project, aprops.tab == "SERVICES")
            self.draw_tab_entry(row, "EDITMODE_HLT", "STRUCTURE", is_ifc_project, aprops.tab == "STRUCTURE")
            self.draw_tab_entry(row, "NLA", "SCHEDULING", is_ifc_project, aprops.tab == "SCHEDULING")
            self.draw_tab_entry(row, "PACKAGE", "FM", True, aprops.tab == "FM")
            self.draw_tab_entry(row, "COMMUNITY", "QUALITY", True, aprops.tab == "QUALITY")
            self.draw_tab_entry(row, "BLENDER", "BLENDER", True, aprops.tab == "BLENDER")
            row.operator("bim.switch_tab", text="", emboss=False, icon="UV_SYNC_SELECT")

            # Yes, that's right.
            row = self.layout.row()
            row.scale_y = 0.2
            for tab in [
                "PROJECT",
                "OBJECT",
                "GEOMETRY",
                "DRAWINGS",
                "SERVICES",
                "STRUCTURE",
                "SCHEDULING",
                "FM",
                "QUALITY",
                "BLENDER",
                "SWITCH",
            ]:
                if aprops.tab == tab:
                    row.prop(aprops, "active_tab", text="", icon="BLANK1")
                else:
                    row.prop(aprops, "inactive_tab", text="", icon="BLANK1", emboss=False)

            row = self.layout.row(align=True)
            row.prop(aprops, "tab", text="")
        except:
            pass  # Prior to load_post, we may not have any area properties setup

    def draw_tab_entry(self, row, icon, tab_name, enabled=True, highlight=False):
        tab_entry = row.row(align=True)
        tab_entry.operator("bim.set_tab", text="", emboss=highlight, icon=icon, depress=True).tab = tab_name
        tab_entry.enabled = enabled


class BIM_PT_tab_project_info(Panel):
    bl_label = "Project Info"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"

    @classmethod
    def poll(cls, context):
        return tool.Blender.is_tab(context, "PROJECT")

    def draw(self, context):
        pass


class BIM_PT_tab_project_setup(Panel):
    bl_label = "Project Setup"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"

    @classmethod
    def poll(cls, context):
        return tool.Blender.is_tab(context, "PROJECT")

    def draw(self, context):
        pass


class BIM_PT_tab_stakeholders(Panel):
    bl_label = "Stakeholders"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        return tool.Blender.is_tab(context, "PROJECT") and tool.Ifc.get()

    def draw(self, context):
        pass


class BIM_PT_tab_collaboration(Panel):
    bl_label = "Collaboration"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"

    @classmethod
    def poll(cls, context):
        return tool.Blender.is_tab(context, "QUALITY")

    def draw(self, context):
        pass


class BIM_PT_tab_grouping_and_filtering(Panel):
    bl_label = "Grouping and Filtering"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_options = {"DEFAULT_CLOSED","HEADER_LAYOUT_EXPAND"}

    @classmethod
    def poll(cls, context):
        return tool.Blender.is_tab(context, "PROJECT") and tool.Ifc.get()

    def draw(self, context):
        pass

    def draw_header(self, context):
        # Draws help button on the right
        row = self.layout.row(align=True)
        row.label(text="")  # empty text occupies the left of the row
        row.operator("bim.open_uri", text="", icon="HELP").uri = \
            "https://docs.ifcopenshell.org/ifcopenshell-python/selector_syntax.html"


class BIM_PT_tab_geometry(Panel):
    bl_label = "Geometry"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"

    @classmethod
    def poll(cls, context):
        return tool.Blender.is_tab(context, "PROJECT") and tool.Ifc.get()

    def draw(self, context):
        pass


class BIM_PT_tab_status(Panel):
    bl_label = "Status"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"

    @classmethod
    def poll(cls, context):
        return tool.Blender.is_tab(context, "SCHEDULING") and tool.Ifc.get()

    def draw(self, context):
        pass


class BIM_PT_tab_resources(Panel):
    bl_label = "Resources"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"

    @classmethod
    def poll(cls, context):
        return tool.Blender.is_tab(context, "SCHEDULING") and tool.Ifc.get()

    def draw(self, context):
        pass


class BIM_PT_tab_cost(Panel):
    bl_label = "Cost"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"

    @classmethod
    def poll(cls, context):
        return tool.Blender.is_tab(context, "SCHEDULING") and tool.Ifc.get()

    def draw(self, context):
        pass


class BIM_PT_tab_sequence(Panel):
    bl_label = "Construction Scheduling"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"

    @classmethod
    def poll(cls, context):
        return tool.Blender.is_tab(context, "SCHEDULING") and tool.Ifc.get()

    def draw(self, context):
        pass


class BIM_PT_tab_structural(Panel):
    bl_label = "Structural"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"

    @classmethod
    def poll(cls, context):
        return tool.Blender.is_tab(context, "STRUCTURE") and tool.Ifc.get()

    def draw(self, context):
        pass


class BIM_PT_tab_services(Panel):
    bl_label = "Services"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"

    @classmethod
    def poll(cls, context):
        return tool.Blender.is_tab(context, "SERVICES") and tool.Ifc.get()

    def draw(self, context):
        pass


class BIM_PT_tab_zones(Panel):
    bl_label = "Zones"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"

    @classmethod
    def poll(cls, context):
        return tool.Blender.is_tab(context, "SERVICES") and tool.Ifc.get()

    def draw(self, context):
        pass


class BIM_PT_tab_quality_control(Panel):
    bl_label = "Quality Control"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"

    @classmethod
    def poll(cls, context):
        return tool.Blender.is_tab(context, "QUALITY")

    def draw(self, context):
        pass


class BIM_PT_tab_clash_detection(Panel):
    bl_label = "Clash Detection"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"

    @classmethod
    def poll(cls, context):
        return tool.Blender.is_tab(context, "QUALITY")

    def draw(self, context):
        pass


class BIM_PT_tab_sandbox(Panel):
    bl_label = "Sandbox"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        return tool.Blender.is_tab(context, "QUALITY")

    def draw(self, context):
        row = self.layout.row()
        row.label(text="More Experimental Than Usual", icon="ERROR")


# Object panel groups
class BIM_PT_tab_object_metadata(Panel):
    bl_label = "Object Metadata"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_order = 1

    @classmethod
    def poll(cls, context):
        return tool.Blender.is_tab(context, "OBJECT") and tool.Ifc.get()

    def draw(self, context):
        pass


class BIM_PT_tab_placement(Panel):
    bl_label = "Placement"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_order = 1

    @classmethod
    def poll(cls, context):
        return tool.Blender.is_tab(context, "GEOMETRY") and tool.Ifc.get()

    def draw(self, context):
        pass


class BIM_PT_tab_representations(Panel):
    bl_label = "Representations"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_order = 1

    @classmethod
    def poll(cls, context):
        return tool.Blender.is_tab(context, "GEOMETRY") and tool.Ifc.get()

    def draw(self, context):
        pass


class BIM_PT_tab_geometric_relationships(Panel):
    bl_label = "Geometric Relationships"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_order = 1
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        return tool.Blender.is_tab(context, "GEOMETRY") and tool.Ifc.get()

    def draw(self, context):
        pass


class BIM_PT_tab_parametric_geometry(Panel):
    bl_label = "Parametric Geometry"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_order = 1
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        return tool.Blender.is_tab(context, "GEOMETRY") and tool.Ifc.get()

    def draw(self, context):
        pass


class BIM_PT_tab_materials(Panel):
    bl_label = "Materials"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_order = 1

    @classmethod
    def poll(cls, context):
        return tool.Blender.is_tab(context, "GEOMETRY") and tool.Ifc.get()

    def draw(self, context):
        pass


class BIM_PT_tab_styles(Panel):
    bl_label = "Styles"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_order = 1

    @classmethod
    def poll(cls, context):
        return tool.Blender.is_tab(context, "GEOMETRY") and tool.Ifc.get()

    def draw(self, context):
        pass


class BIM_PT_tab_profiles(Panel):
    bl_label = "Profiles"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_order = 1

    @classmethod
    def poll(cls, context):
        return tool.Blender.is_tab(context, "GEOMETRY") and tool.Ifc.get()

    def draw(self, context):
        pass


class BIM_PT_tab_sheets(Panel):
    bl_label = "Sheets"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_order = 1

    @classmethod
    def poll(cls, context):
        return tool.Blender.is_tab(context, "DRAWINGS") and tool.Ifc.get()

    def draw(self, context):
        pass


class BIM_PT_tab_drawings(Panel):
    bl_label = "Drawings"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_order = 1

    @classmethod
    def poll(cls, context):
        return tool.Blender.is_tab(context, "DRAWINGS") and tool.Ifc.get()

    def draw(self, context):
        pass


class BIM_PT_tab_schedules(Panel):
    bl_label = "Schedules"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_order = 1

    @classmethod
    def poll(cls, context):
        return tool.Blender.is_tab(context, "DRAWINGS") and tool.Ifc.get()

    def draw(self, context):
        pass


class BIM_PT_tab_references(Panel):
    bl_label = "References"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_order = 1

    @classmethod
    def poll(cls, context):
        return tool.Blender.is_tab(context, "DRAWINGS") and tool.Ifc.get()

    def draw(self, context):
        pass


class BIM_PT_tab_misc(Panel):
    bl_label = "Misc."
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_order = 1
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        return tool.Blender.is_tab(context, "OBJECT") and tool.Ifc.get()

    def draw(self, context):
        pass


class BIM_PT_tab_handover(Panel):
    bl_label = "Commissioning and Handover"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_order = 1

    @classmethod
    def poll(cls, context):
        return tool.Blender.is_tab(context, "FM")

    def draw(self, context):
        pass


class BIM_PT_tab_operations(Panel):
    bl_label = "Operations and Maintenance"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_order = 2

    @classmethod
    def poll(cls, context):
        return tool.Blender.is_tab(context, "FM")

    def draw(self, context):
        pass


class UIData:
    data = {}
    is_loaded = False

    @classmethod
    def load(cls):
        cls.data = {"version": cls.version()}
        cls.is_loaded = True

    @classmethod
    def version(cls):
        return tool.Blender.get_blenderbim_version()


def draw_statusbar(self, context):
    if not UIData.is_loaded:
        UIData.load()
    text = f"BlenderBIM Add-on v{UIData.data['version']}"
    self.layout.label(text=text)


def draw_custom_context_menu(self, context):
    # https://blender.stackexchange.com/a/275555/86891
    if (
        not hasattr(context, "button_pointer")
        or not hasattr(context, "button_prop")
        or not hasattr(context.button_prop, "identifier")
    ):
        return
    prop = context.button_pointer
    prop_name = context.button_prop.identifier
    prop_value = getattr(prop, prop_name, None)
    if prop_value is None:
        return
    version = tool.Ifc.get_schema()
    layout = self.layout

    if isinstance(context.button_pointer, Attribute):
        description = getattr(context.button_pointer, "description", None)
        ifc_class = getattr(context.button_pointer, "ifc_class", "")
        if ifc_class:
            try:
                url = get_entity_doc(version, context.button_pointer.ifc_class).get("spec_url", "")
            except RuntimeError:  # It's not an Entity Attribute. Let's try a Property Set attribute.
                doc = get_property_set_doc(version, context.button_pointer.ifc_class)
                if doc:
                    url = doc.get("spec_url", "")
                else:  # It's a custom property set. No URL available
                    url = ""
        if description:
            layout.separator()
            op_description = layout.operator("bim.show_description", text="IFC Description", icon="INFO")
            op_description.attr_name = getattr(context.button_pointer, "name", "")
            op_description.description = description
            op_description.url = url
    else:
        # Ugly but we can't know which type of data is under the cursor so we test everything until it clicks
        try:
            docs = get_entity_doc(version, prop_value)
            if docs is None:
                raise RuntimeError
        except (RuntimeError, AttributeError):
            try:
                docs = get_type_doc(version, prop_value)
                if docs is None:
                    raise RuntimeError
            except (RuntimeError, AttributeError):
                try:
                    docs = get_property_set_doc(version, prop_value)
                    if docs is None:
                        raise RuntimeError
                except (RuntimeError, AttributeError):
                    pass
        if docs:
            url = docs.get("spec_url", "")
            if url:
                layout.separator()
                url_op = layout.operator("bim.open_webbrowser", icon="URL", text="Online IFC Documentation")
                url_op.url = url
