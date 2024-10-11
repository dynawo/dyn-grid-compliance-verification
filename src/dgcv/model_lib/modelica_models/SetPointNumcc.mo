model SetPointNumcc "Fixed set-point throughout a simulation"
  import Dynawo.Connectors;

  Connectors.ZPin setPoint(value(start = Value0)) "Set point value";

  parameter Real Value0 "Start value of the set-point model";

equation
  setPoint.value = Value0;

  annotation(preferredView = "text");
end SetPointNumcc;
