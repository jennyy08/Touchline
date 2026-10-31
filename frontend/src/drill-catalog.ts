/** Content only: adding a drill does not require changing the library layout. */
export interface Drill {
  id: string;
  name: string;
  focus: string;
  description: string;
  equipment: string;
  space: string;
  steps: string[];
  camera: string;
  measures: string[];
  limitation: string;
  analysis: string;
  live?: string;
  preview: string;
  poster: string;
}
export const drills: Drill[] = [
  {
    id: "juggling",
    name: "Juggling",
    focus: "Touch & control",
    description:
      "Find a softer touch. Keep the ball close, reset, and go again.",
    equipment: "One ball",
    space: "Room to move safely in every direction",
    steps: [
      "Start with a gentle drop and one controlled touch.",
      "Try to keep the ball close enough for the next touch. Reset whenever you need.",
      "Build a short sequence at your own pace. Focus on control before chasing a count.",
    ],
    camera:
      "Keep your whole body and the ball’s highest point in frame. Leave space on either side and keep the camera still.",
    measures: [
      "Estimated airborne contacts",
      "Touch timestamps and tracking gaps",
    ],
    limitation:
      "Cropped or hidden contacts can be missed. The count is an estimate, not a technique assessment.",
    analysis: "/juggling.html",
    live: "/live.html",
    preview: "/previews/juggling.mp4",
    poster: "/previews/juggling.jpg",
  },
  {
    id: "side-to-side",
    name: "Side to side",
    focus: "Movement & turns",
    description:
      "Two markers. A little room. Work on reaching each end with control.",
    equipment: "One ball · two visible markers",
    space: "A clear lane between your markers",
    steps: [
      "Place two markers with enough space to dribble between them.",
      "Move the ball from one marker to the other, then turn and return.",
      "Choose a comfortable pace. Reaching or passing the marker is okay; keep the ball under control.",
    ],
    camera:
      "Film the lane from the side so you move across the screen. Include both markers and extra space beyond each end. A stable elevated phone helps.",
    measures: [
      "Estimated turns and completed lengths",
      "Time between turns and changes in pace",
      "Reaching the selected marker boundaries",
    ],
    limitation:
      "Times are relative to your setup, not speed in metres per second. Some offscreen turns are inferred; inspect the replay.",
    analysis: "/dribbling.html#upload-panel",
    preview: "/previews/side-to-side.mp4",
    poster: "/previews/side-to-side.jpg",
  },
  {
    id: "toe-taps",
    name: "Toe taps",
    focus: "Rhythm & coordination",
    description:
      "Alternate feet on top of the ball. Find a rhythm you can keep.",
    equipment: "One ball",
    space: "A small, clear practice area",
    steps: [
      "Start with the ball still and both feet on the ground.",
      "Lightly touch the top of the ball with one foot, then switch feet.",
      "Aim for a steady rhythm and a ball that stays close. Slow down or reset when needed.",
    ],
    camera:
      "Keep both feet and the entire ball visible, with room for drift. Use a stationary phone; avoid a view where one foot constantly hides the other.",
    measures: [
      "Estimated taps",
      "Individual contact timestamps for reviewing rhythm",
    ],
    limitation:
      "Overlapping shoes and hidden contacts can cause missed or extra taps. Opening held poses are excluded.",
    analysis: "/toe-taps.html",
    preview: "/previews/toe-taps.mp4",
    poster: "/previews/toe-taps.jpg",
  },
];
export const findDrill = (id: string | null) =>
  drills.find((drill) => drill.id === id);
