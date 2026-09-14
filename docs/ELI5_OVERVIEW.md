# Neurodot in simple terms

## The short version

Neurodot is a counting assistant for fluorescence microscopy images stored as
Imaris `.ims` files.

Think of it as giving a careful lab assistant three jobs:

1. You show it where the relevant anatomy is.
2. Cellpose circles things that look like cells.
3. Neurodot keeps only the circles that obey your anatomical rules and writes
   them back into editable Imaris files.

The scientist still decides what the tissue means. Neurodot repeats the
mechanical counting and file-writing steps consistently.

## What happens during one run

### 1. The user chooses the job

The startup window asks for an input folder, an output folder, an output-name
tag, a Cellpose model, and the diameter of the output Imaris Spots. The portable
release already contains the normal local model. The standard Spot diameter is
5.0 µm; changing it changes the saved Spot size and centre-point width, not the
cell-detection decisions.

### 2. Neurodot reads each image

An `.ims` file is a structured image container. Neurodot reads its pixels,
channel information, image size, and physical dimensions. It creates a flat
maximum-intensity preview so the user can work with the whole section.

### 3. The user teaches it the anatomy

The user places the bottom and top of the midline first. Neurodot puts the
centre point exactly halfway between them. The centre remains editable because
downstream analysis still needs it as its own landmark.

The user then places the left and right `si`, `bo`, and `to` landmarks. These
points define one counting rectangle for each hemisphere.

### 4. The user defines visibility

For every channel, the user can set black and white exposure values using a
weak positive cell and representative background. An image can also use the
series average. Once exposure is accepted, the preview shows the real saved
setting instead of returning to the temporary landmark-placement exposure.

### 5. Cellpose proposes cells

Cellpose receives the exposure-adjusted image and returns one labelled shape
per detected object. Neurodot uses the geometric centre of each accepted shape
as the Spot position.

### 6. Neurodot applies the counting rules

The rules behave like overlapping paper cut-outs:

- The Spot must be on the correct side of the midline.
- The Spot must be inside that side's landmark rectangle.
- If Dorsal or Ventral is selected, it must also be in that half.
- An inclusion ROI keeps only Spots inside the drawn ROI.
- An exclusion ROI rejects Spots inside the drawn ROI.

The Cellpose preview uses these same rules. A preview message shows how many
detected instances remain inside the active counting areas.

### 7. Neurodot creates two editable outputs

Neurodot copies the source image into two new files, one for the left side and
one for the right side. It adds the detected Spots, landmarks, rotation group,
and the chosen channel display ranges. Imaris can still inspect, edit, and save
the resulting Spot groups.

## What Neurodot deliberately does not decide

Neurodot does not know whether a landmark is biologically correct. It does not
know whether the selected background is representative, and it cannot prove
that every Cellpose object is a real cell. The operator must review the image,
preview, counts, and unusual sections.

## Useful words

- **MIP:** A flat image made by keeping the brightest pixel through the Z
  stack.
- **Exposure:** The black and white display values used to prepare the image
  for Cellpose.
- **Landmark:** A point placed by the scientist to describe the anatomy.
- **ROI:** A hand-drawn region of interest that includes or excludes detections.
- **Centroid:** The geometric middle of a detected Cellpose shape.
- **Placeholder:** A deliberately separated dummy Spot used when a channel has
  no real Spots, so the Imaris Spot-group structure remains intact.
- **Schema donor:** A known-good Imaris file whose native Spot structure is
  copied into the output before Neurodot fills in the new coordinates.
