partial model BaseWTU4B "Base model for WECC Wind Turbine 4B"
  import Modelica;
  import Dynawo;

  extends BaseWTU4;

equation
  connect(OmegaRef.y, wecc_reec.omegaGPu) annotation(
    Line(points = {{-179, 38}, {-175, 38}, {-175, -60}, {-85, -60}, {-85, -11}}, color = {0, 0, 127}));

  annotation(
    preferredView = "diagram");
end BaseWTU4B;
