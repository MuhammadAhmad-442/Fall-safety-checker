# Fall-safety-checker
A pyRevit tool to detect unsafe floor edges in Revit models by checking exposed boundaries and highlighting fall risks.

🔍 Current Features
Filters floor edges above 6 feet.
Splits edges into smaller segments for better detection.
Checks if a region (~30 cm) around each edge is exposed.
Marks edges as unsafe (red) if more than 70% of the region is uncovered (avoids false positives from walls and nearby elements).

🚧 Planned Improvements
Detect floors with and without surrounding walls.
Separate floor elements from similar objects (e.g., pavements).
Identify floor corners on construction models.
Add export options and floor gap detection.


