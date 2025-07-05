from pyrevit import revit, DB, script, forms
from System.Collections.Generic import List
import time

# Default Parameters
MIN_FLOOR_HEIGHT = 6.0  # Minimum height for safety check
MAX_SELECTION = 50
BUFFER_DISTANCE = 0.3  # 30 cm buffer around edges
SEGMENT_LENGTH = 0.3  # Smaller segments for finer edge checks
MIN_COVER_PERCENTAGE = 0.3  # Minimum percentage of edge length that must be covered by barriers
MAX_UNCOVERED_PERCENTAGE = 0.7  # Maximum allowed uncovered percentage before flagging

def get_elements(categories):
    doc = revit.doc
    elements = []
    for category in categories:
        elements.extend(list(DB.FilteredElementCollector(doc)
                             .OfCategory(category)
                             .WhereElementIsNotElementType()
                             .ToElements()))
    return elements


def get_floor_edges(floor):
    edges = []
    face_refs = DB.HostObjectUtils.GetTopFaces(floor)
    for face_ref in face_refs:
        face = floor.GetGeometryObjectFromReference(face_ref)
        if isinstance(face, DB.Face):
            edge_array = face.EdgeLoops
            for edge_loop in edge_array:
                for edge in edge_loop:
                    edges.append(edge.AsCurve())
    return edges


def split_curve(curve):
    segments = []
    try:
        curve_length = curve.Length
        num_segments = max(1, int(curve_length / SEGMENT_LENGTH))
        for i in range(num_segments):
            param = curve.GetEndParameter(0) + (i * (curve_length / num_segments))
            segments.append(curve.Evaluate(param, True))
    except:
        segments.append(curve.Evaluate(0.5, True))
    return segments


def is_barrier_near_point(point, barriers):
    for barrier in barriers:
        bbox = barrier.get_BoundingBox(None)
        if not bbox:
            continue
        expanded_bbox = DB.BoundingBoxXYZ()
        expanded_bbox.Min = bbox.Min - DB.XYZ(BUFFER_DISTANCE, BUFFER_DISTANCE, BUFFER_DISTANCE)
        expanded_bbox.Max = bbox.Max + DB.XYZ(BUFFER_DISTANCE, BUFFER_DISTANCE, BUFFER_DISTANCE)
        if (expanded_bbox.Min.X <= point.X <= expanded_bbox.Max.X and
                expanded_bbox.Min.Y <= point.Y <= expanded_bbox.Max.Y and
                expanded_bbox.Min.Z <= point.Z <= expanded_bbox.Max.Z):
            return True
    return False


def classify_edges(floors, barriers):
    exposed_floors = []
    
    for floor in floors:
        bbox = floor.get_BoundingBox(None)
        if not bbox or bbox.Min.Z < MIN_FLOOR_HEIGHT:
            continue

        edges = get_floor_edges(floor)
        for edge in edges:
            points = split_curve(edge)
            covered_points = [p for p in points if is_barrier_near_point(p, barriers)]
            cover_percentage = len(covered_points) / float(len(points)) if points else 0
            uncovered_percentage = 1 - cover_percentage

            if uncovered_percentage > MAX_UNCOVERED_PERCENTAGE:
                print("Floor ID {} Uncovered Percentage: {:.2f}%".format(floor.Id.IntegerValue, uncovered_percentage * 100))
                exposed_floors.append(floor)
                break

    return exposed_floors


def apply_highlight(elements, color=(255, 50, 50), transparency=60):
    if not elements:
        print("No elements to highlight")
        return

    print("Highlighting {} elements".format(len(elements)))
    doc = revit.doc
    ogs = DB.OverrideGraphicSettings()
    highlight_color = DB.Color(color[0], color[1], color[2])

    collector = DB.FilteredElementCollector(doc).OfClass(DB.FillPatternElement)
    solid_fill = next(fp for fp in collector if fp.GetFillPattern().IsSolidFill)

    ogs.SetSurfaceForegroundPatternColor(highlight_color)
    ogs.SetSurfaceForegroundPatternId(solid_fill.Id)
    ogs.SetSurfaceTransparency(transparency)

    t = DB.Transaction(doc, "Highlight Elements")
    t.Start()
    try:
        for element in elements:
            doc.ActiveView.SetElementOverrides(element.Id, ogs)
        t.Commit()
    except Exception as e:
        print("Highlight Error:", e)
        t.RollBack()


if __name__ == "__main__":
    start_time = time.time()
    print("Deploying Falcon-Eye: Edge Sentinel")
    floors = get_elements([DB.BuiltInCategory.OST_Floors])
    barriers = get_elements([DB.BuiltInCategory.OST_Walls, DB.BuiltInCategory.OST_StairsRailing, DB.BuiltInCategory.OST_CurtainWallPanels])

    exposed_floors = classify_edges(floors, barriers)
    print("Total Floors Checked: {}".format(len(floors)))
    print("Exposed Floors Detected: {}".format(len(exposed_floors)))

    if exposed_floors:
        apply_highlight(exposed_floors)
        exposed_ids = List[DB.ElementId]([floor.Id for floor in exposed_floors])
        selected = exposed_ids[:MAX_SELECTION]
        revit.uidoc.Selection.SetElementIds(selected)
        print("Selected {} out of {} elements".format(len(selected), len(exposed_ids)))
    else:
        print("No Exposed Floors Detected")

    runtime = time.time() - start_time
    print("Runtime: {:.2f} seconds".format(runtime))
