// How the charts treat years without data. A gap of up to BRIDGE years is drawn as the straight line between its ends.
// A longer gap stays open, so no chart draws a trend across decades the source never measured.
// Twenty-five years bridges the sparse surveys of literacy or poverty, but not Germany's V-Dem gap of 1945 to 1990.
export const BRIDGE = 25;
