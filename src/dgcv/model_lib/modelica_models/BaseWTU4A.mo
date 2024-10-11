partial model BaseWTU4A "Partial base model for WECC Wind Turbine 4A"
  import Modelica;
  import Dynawo;

  extends Dynawo.Electrical.Controls.WECC.Parameters.ParamsDriveTrain;
  extends BaseWTU4;

  Dynawo.Electrical.Controls.WECC.Mechanical.DriveTrainPmConstant driveTrainPmConstrant(Dshaft = Dshaft, Hg = Hg, Ht = Ht, Kshaft = Kshaft, PInj0Pu = PInj0Pu, PePu(start = PInj0Pu)) annotation(
    Placement(visible = true, transformation(origin = {-91, -41}, extent = {{-10, -5}, {10, 5}}, rotation = 0)));

equation
  connect(driveTrainPmConstrant.omegaGPu, wecc_reec.omegaGPu) annotation(
    Line(points = {{-86, -35}, {-85, -35}, {-85, -11}}, color = {0, 0, 127}));
  connect(injector.PInjPuSn, driveTrainPmConstrant.PePu) annotation(
    Line(points = {{12, -4}, {25, -4}, {25, -40}, {-79, -40}}, color = {0, 0, 127}));
  connect(OmegaRef.y, driveTrainPmConstrant.omegaRefPu) annotation(
    Line(points = {{-179, 38}, {-175, 38}, {-175, -60}, {-110, -60}, {-110, -40}, {-101, -40}}, color = {0, 0, 127}));

  annotation(
    preferredView = "diagram",
    Diagram(coordinateSystem(grid = {1, 1}, extent = {{-180, -60}, {120, 60}})));
end BaseWTU4A;
