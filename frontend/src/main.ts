// Keep previously shared juggling replay URLs working after introducing a home page.
if (new URLSearchParams(location.search).has("job")) {
  void import("./juggling");
} else {
  void import("./library");
}
export {};
