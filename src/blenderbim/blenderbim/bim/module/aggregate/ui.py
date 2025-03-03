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

from bpy.types import Panel
from blenderbim.bim.module.aggregate.data import AggregateData
from blenderbim.bim.module.group.data import GroupsData, ObjectGroupsData
from blenderbim.bim.ifc import IfcStore


class BIM_PT_aggregate(Panel):
    bl_label = "Aggregates"
    bl_idname = "BIM_PT_aggregate"
    bl_options = {"DEFAULT_CLOSED"}
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    bl_parent_id = "BIM_PT_tab_object_metadata"

    @classmethod
    def poll(cls, context):
        if not context.active_object:
            return False
        props = context.active_object.BIMObjectProperties
        if not props.ifc_definition_id:
            return False
        if not IfcStore.get_element(props.ifc_definition_id):
            return False
        if not IfcStore.get_file().by_id(props.ifc_definition_id).is_a("IfcObjectDefinition"):
            return False
        return True

    def draw(self, context):
        layout = self.layout
        if not AggregateData.is_loaded:
            AggregateData.load()

        props = context.active_object.BIMObjectAggregateProperties

        if props.is_editing:
            row = layout.row(align=True)
            row.prop(props, "relating_object", text="")
            if props.relating_object:
                op = row.operator("bim.aggregate_assign_object", icon="CHECKMARK", text="")
                op.relating_object = props.relating_object.BIMObjectProperties.ifc_definition_id
            row.operator("bim.disable_editing_aggregate", icon="CANCEL", text="")
        else:
            row = layout.row(align=True)
            if AggregateData.data["has_relating_object"]:
                row.label(text=AggregateData.data["relating_object_label"], icon="TRIA_UP")
                op = row.operator("bim.select_aggregate", icon="OBJECT_DATA", text="")
                op.obj = context.active_object.name
                op.select_parts = False
                op = row.operator("bim.select_aggregate", icon="RESTRICT_SELECT_OFF", text="")
                op.obj = context.active_object.name
                op.select_parts = True
                row.operator("bim.enable_editing_aggregate", icon="GREASEPENCIL", text="")
                row.operator("bim.add_aggregate", icon="ADD", text="")
                op = row.operator("bim.aggregate_unassign_object", icon="X", text="")
            else:
                row.label(text="No Aggregate", icon="TRIA_UP")
                row.operator("bim.enable_editing_aggregate", icon="GREASEPENCIL", text="")
                row.operator("bim.add_aggregate", icon="ADD", text="")

        row = layout.row(align=True)
        total_parts = AggregateData.data["total_parts"]
        if total_parts == 0:
            row.label(text="No Parts", icon="TRIA_DOWN")
        elif total_parts == 1:
            row.label(text="1 Part", icon="TRIA_DOWN")
        else:
            row.label(text=f"{total_parts} Parts", icon="TRIA_DOWN")

        if AggregateData.data["has_related_objects"]:
            op = row.operator("bim.select_parts", icon="RESTRICT_SELECT_OFF", text="")
            op.obj = context.active_object.name

        ifc_class = AggregateData.data["ifc_class"]
        part_class = ""
        if ifc_class == "IfcBuilding":
            part_class = "IfcBuildingStorey"
        elif ifc_class == "IfcSite":
            part_class = "IfcBuilding"
        elif ifc_class == "IfcProject":
            part_class = "IfcSite"
        if part_class != "":
            op = layout.operator("bim.add_part_to_object", text="Add " + part_class.lstrip("Ifc"))
            op.part_class = part_class
            op.obj = context.active_object.name
            
            
class BIM_PT_linked_aggregate(Panel):
    bl_label = "Linked Aggregates"
    bl_idname = "BIM_PT_linked_aggregate"
    bl_options = {"DEFAULT_CLOSED"}
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    bl_order = 2
    bl_parent_id = "BIM_PT_aggregate"

    @classmethod
    def poll(cls, context):
        if not context.active_object:
            return False
        props = context.active_object.BIMObjectProperties
        if not props.ifc_definition_id:
            return False
        if not IfcStore.get_element(props.ifc_definition_id):
            return False
        if not IfcStore.get_file().by_id(props.ifc_definition_id).is_a("IfcObjectDefinition"):
            return False
        return True

    def draw(self, context):
        layout = self.layout
        if not AggregateData.is_loaded:
            AggregateData.load()

        props = context.active_object.BIMObjectAggregateProperties
        row = layout.row(align=True)
        row.label(text="Advanced Users Only", icon="ERROR")
        row = layout.row(align=True)
        
        if type(AggregateData.data['total_linked_aggregate']) is int:
            if AggregateData.data['total_linked_aggregate'] > 0:
                row.label(text=f"{AggregateData.data['total_linked_aggregate']} Linked Aggregates")
                op = row.operator("bim.select_linked_aggregates", text="", icon="OUTLINER_DATA_POINTCLOUD")
                op.select_parts = False
                op = row.operator("bim.select_linked_aggregates", text="", icon="OUTLINER_OB_POINTCLOUD")
                op.select_parts = True
                row.operator("bim.refresh_linked_aggregate", text="", icon="FILE_REFRESH")
                op = row.operator("bim.break_link_to_other_aggregates", text="", icon="X")
        else:
            row.label(text="No Linked Aggregates")
            
        

