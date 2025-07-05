from pyrevit import revit, DB, script

def reset_all_highlights():
    doc = revit.doc
    elements = DB.FilteredElementCollector(doc).WhereElementIsNotElementType().ToElements()
    ogs = DB.OverrideGraphicSettings()
    t = DB.Transaction(doc, "Clear Highlights")
    t.Start()
    try:
        for element in elements:
            doc.ActiveView.SetElementOverrides(element.Id, ogs)
        t.Commit()
    except Exception as e:
        print("Reset Error:", e)
        t.RollBack()

reset_all_highlights()
