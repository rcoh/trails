export const Units = {
  km: {
    long: "kilometers",
    short: "km"
  },
  mi: {
    long: "miles",
    short: "miles"
  },
  m: {
    long: "meters",
    short: "m"
  },
  ft: {
    long: "feet",
    short: "ft"
  }
};

export const UnitSystems = {
  metric: {
    length: Units.km,
    height: Units.m,
    name: "metric"
  },
  imperial: {
    name: "imperial",
    length: Units.mi,
    height: Units.ft
  }
};
