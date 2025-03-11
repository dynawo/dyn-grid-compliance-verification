model SetPointOmega "Fixed set-point throughout a simulation"
  import Dynawo.Connectors;

  Connectors.ImPin omegaPu(value(start = Value0)) "Set point value";
  Connectors.ImPin omegaRefPu "omegaRefPu";
  Connectors.BPin running(value(start = true)) "Indicates if the component is running or not";

  parameter Real Value0 "Start value of the set-point model";

equation
  omegaPu.value = Value0;
  running.value = true;

  annotation(preferredView = "text");
end SetPointOmega;
