model GovernorI8SM

  import Dynawo;

  parameter Dynawo.Types.ActivePowerPu Pm0Pu "Initial mechanical power in pu (base PNom)";

  Modelica.Blocks.Interfaces.RealInput omegaPu(start = 1) annotation(
    Placement(visible = true, transformation(origin = {-112, -40}, extent = {{-12, -12}, {12, 12}}, rotation = 0), iconTransformation(origin = {-112, -20}, extent = {{-12, -12}, {12, 12}}, rotation = 0)));
  Modelica.Blocks.Sources.Constant OmegaRefPu(k = 1)  annotation(
    Placement(visible = true, transformation(origin = {-110, 0}, extent = {{-10, -10}, {10, 10}}, rotation = 0)));
  Modelica.Blocks.Math.Add add(k2 = -1)  annotation(
    Placement(visible = true, transformation(origin = {-64, -6}, extent = {{-10, -10}, {10, 10}}, rotation = 0)));
  Modelica.Blocks.Math.Gain gain(k = 5)  annotation(
    Placement(visible = true, transformation(origin = {-24, -6}, extent = {{-10, -10}, {10, 10}}, rotation = 0)));
  Modelica.Blocks.Math.Add add1 annotation(
    Placement(visible = true, transformation(origin = {16, 34}, extent = {{-10, -10}, {10, 10}}, rotation = 0)));
  Modelica.Blocks.Interfaces.RealOutput PmPu(start = Pm0Pu) annotation(
    Placement(visible = true, transformation(origin = {110, 34}, extent = {{-10, -10}, {10, 10}}, rotation = 0), iconTransformation(origin = {110, -2}, extent = {{-10, -10}, {10, 10}}, rotation = 0)));
  Modelica.Blocks.Interfaces.RealInput PmRefPu(start = Pm0Pu) annotation(
    Placement(visible = true, transformation(origin = {-112, 46}, extent = {{-12, -12}, {12, 12}}, rotation = 0), iconTransformation(origin = {-112, -20}, extent = {{-12, -12}, {12, 12}}, rotation = 0)));
  Modelica.Blocks.Continuous.FirstOrder firstOrder(T = 2.5, k = 1)  annotation(
    Placement(visible = true, transformation(origin = {66, 34}, extent = {{-10, -10}, {10, 10}}, rotation = 0)));
  Modelica.Blocks.Math.Division division annotation(
    Placement(visible = true, transformation(origin = {-64, 40}, extent = {{-10, -10}, {10, 10}}, rotation = 0)));
equation

  connect(OmegaRefPu.y, add.u1) annotation(
    Line(points = {{-99, 0}, {-76, 0}}, color = {0, 0, 127}));
  connect(omegaPu, add.u2) annotation(
    Line(points = {{-112, -40}, {-76, -40}, {-76, -12}}, color = {0, 0, 127}));
  connect(add.y, gain.u) annotation(
    Line(points = {{-53, -6}, {-36, -6}}, color = {0, 0, 127}));
  connect(gain.y, add1.u2) annotation(
    Line(points = {{-12, -6}, {4, -6}, {4, 28}}, color = {0, 0, 127}));
  connect(add1.y, firstOrder.u) annotation(
    Line(points = {{28, 34}, {54, 34}}, color = {0, 0, 127}));
  connect(firstOrder.y, PmPu) annotation(
    Line(points = {{78, 34}, {110, 34}}, color = {0, 0, 127}));
  connect(PmRefPu, division.u1) annotation(
    Line(points = {{-112, 46}, {-76, 46}}, color = {0, 0, 127}));
  connect(omegaPu, division.u2) annotation(
    Line(points = {{-112, -40}, {-90, -40}, {-90, 34}, {-76, 34}}, color = {0, 0, 127}));
  connect(division.y, add1.u1) annotation(
    Line(points = {{-52, 40}, {4, 40}}, color = {0, 0, 127}));  protected
  annotation(
    uses(Modelica(version = "3.2.3"), Dynawo(version = "1.0.1")));

end GovernorI8SM;
